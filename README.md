> [!warning]
> I've not used/maintained this project for over 5 years. I've no idea if it still even works!

# Markdown -> [Outline](https://getoutline.com) sync

A github action to sync markdown files to your outline docs

Features:
- Creates/updates the markdown content of your outline docs
- All docs have to be in the same colletion (for now)
- Automatically parses and converts `mermaid`/`plantuml` diagrams to images (Powered by the diagram rendering service provided by https://kroki.io/#how)

## Features


### Diagram conversion

I want to add a diagram to a markdown file, I can add:

    ```mermaid
    graph TD
    A[Christmas] -->|Get money| B(Go shopping)
    B --> C{Let me think}
    C -->|One| D[Laptop]
    C -->|Two| E[iPhone]
    C -->|Three| F[fa:fa-car Car]
    ```

Which will result in the following being rendered in the outline page:

![mermaid diagram](https://kroki.io/mermaid/svg/eNpLL0osyFAIceFyjHbOKMosLslNLI5V0NW1q3FPLVHIzc9LraxRcNJwz1cozsgvKMjMS9fkcgLJKzhX-4BUpCqUZGTmZddyOYN1-eel1ii4RPskFpTkF8RCBUPK82sUXKMzAzKA5sEFM4pSgWrdotMSrdISdZMTixScE4tiAXpCLw8=)


## Installation (Github action)

The action provided by this project needs a surrounding workflow. The following example workflow shows how one would have github actions render, sync and commit updated markdown frontmatter for the `main` branch. The workflow will only run when markdown files have been updated and not commit if no changes are made.


1. Add a `.github/workflows/outline_sync.yml` file containing:

  ```yaml
  name: 'Sync docs to outline'

  on:
    push:
      paths:
        - '**/*.md'
      branches:
        - "main"

  jobs:
    outline:

      name: "Sync markdown to outline"
      runs-on: ubuntu-latest

      steps:
      - uses: actions/checkout@v2
        with:
          fetch-depth: 2

      - name: get changed files
        id: getfile
        run: |
          echo "::set-output name=files::$(git diff-tree --no-commit-id --name-only -r ${{ github.sha }} | grep -e '.*\.md$' | xargs)"

      - name: md files changed
        run: |
          echo ${{ steps.getfile.outputs.files }}

      - name: Sync to outline
        if: steps.getfile.outputs.files
        uses: benhowes/outline-sync-action@v1.0.0
        with:
          files: ${{ steps.getfile.outputs.files }}
        env:
          OUTLINE_API_KEY: ${{secrets.OUTLINE_API_KEY}}
          OUTLINE_COLLECTION_ID: ${{secrets.OUTLINE_COLLECTION_ID}}

      - name: show changes
        id: changes
        run: |
          echo "::set-output name=files::$(git status --porcelain | sed -e 's!.*/!!' | xargs)"

      - name: md files tocommit
        run: |
          echo ${{ steps.changes.outputs.files }}

      - name: Commit files
        if: steps.changes.outputs.files
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git commit -m "Updated markdown [ci skip]" -a

      - name: Push changes
        if: steps.changes.outputs.files
        uses: ad-m/github-push-action@master
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          branch: ${{ github.ref }}


  ```

1. Create secrets:
  - `OUTLINE_API_KEY`: Create in your outline account settings (Settings -> API Tokens)
  - `OUTLINE_COLLECTION_ID`: I had to use my web browsers dev tools to find the UUID of the collection I wanted to use.

1. Push to `main`

## Roadmap

- [x] Basic github action
- [ ] Allow updating published status
- [ ] Support for sub pages (complex, needs some dependency resolution)
- [ ] Support for attachments
- [ ] Tests
