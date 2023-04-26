#!/usr/local/bin/python3.8
import argparse
from pathlib import Path
import time
import os

from dotenv import load_dotenv
import frontmatter
import marko
from marko.md_renderer import MarkdownRenderer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .elements import RenderableMermaid
from .outlineapi import OutlineApi

load_dotenv()

markdown_parser = marko.Markdown(
    renderer=MarkdownRenderer, extensions=[RenderableMermaid]
)


OUTLINE_REQUIRED_METADATA_KEYS = ("title",)
outline_client = OutlineApi(
    os.environ["OUTLINE_API_KEY"], base_url=os.getenv("OUTLINE_BASE_URL")
)
collection_id = os.environ["OUTLINE_COLLECTION_ID"]

WARNING_HEADER = f""":::info
This page is automatically synced from [GitHub](https://github.com/{os.getenv('GITHUB_REPOSITORY')})
:::
"""


def process_file(filename):
    print(f"Processing {filename}... ", end="")
    file_path = Path(filename)

    document = frontmatter.loads(file_path.read_text())
    new_file = markdown_parser.convert(WARNING_HEADER + document.content)

    print(f"Syncing... ", end="")

    if not all(key in document for key in OUTLINE_REQUIRED_METADATA_KEYS):
        print()
        print(f"Unable to sync {filename} due to missing required metadata.")

    if "doc_id" in document:
        # Update a doc
        response = outline_client.document_update(
            doc_id=document["doc_id"], title=document["title"], text=new_file
        )
    else:
        # Create a new doc
        response = outline_client.document_create(
            title=document["title"],
            collection_id=collection_id,
            text=new_file,
            publish=True,
        )
        document["doc_id"] = response["data"]["id"]
        file_path.write_text(frontmatter.dumps(document))

    print("Done.")


class RerenderEventHandler(FileSystemEventHandler):
    """Watchdog handler to re-render when we see a change which GFMD can process."""

    def __init__(self):
        self.debounce_interval = 1  # seconds
        self.debounce_list = {}  # path -> seen time

    def debounce_allow(self, event):
        """Return True if the event is allowed.

        Because GFMD modifies files, we generate new filesystem events when re-writing the updated markdown.
        To counter this, we have to ignore the resulting events.
        """
        current_time = time.monotonic()

        if event.src_path in self.debounce_list:
            if (
                current_time
                < self.debounce_list[event.src_path] + self.debounce_interval
            ):
                return False

        self.debounce_list[event.src_path] = current_time
        return True

    def render(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".md"):
            return
        if not self.debounce_allow(event):
            return
        process_file(event.src_path)

    def on_created(self, event):
        self.render(event)

    def on_modified(self, event):
        self.render(event)


def watch(folders):
    event_handler = RerenderEventHandler()
    observer = Observer()
    for folder in folders:
        observer.schedule(event_handler, str(folder), recursive=True)
    observer.start()
    print("Watching for markdown file changes")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        print("Exiting")


def run():

    # Parse program input
    parser = argparse.ArgumentParser(
        description="Updated embedded mermaid diagrams in markdown."
    )
    parser.add_argument(
        "files",
        metavar="file",
        type=str,
        nargs="*",
        help="The files to render. Parse none to render all files.",
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Watch for changes and re-run on changes.",
    )
    args = parser.parse_args()
    files = args.files

    if args.watch:
        # Run in watch mode.
        if not files:
            files = [Path(".")]

        for folder in files:
            if not Path(folder).is_dir():
                raise Exception("Watching requires that you specify only directories")

        watch(files)

    else:
        # One shot process
        # If no files passed, run on everything
        if not files:
            files = Path(".").rglob("*.md")

        for file in files:
            process_file(file)


if __name__ == "__main__":
    run()
