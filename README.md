# bibtexcleaner

Rephrases BibTeX entries to match the formatting guidelines. 

To this end, only a single file is supported. In case something is written in a different file, it would be best to copy everything into a single file. Note that keys of `proceedings` are automatically updated if `title` is in the correct format.


## Installation
```
git clone https://github.com/automl-private/bibtex-cleaner
cd bibtex-cleaner
conda create -n bibtexcleaner python=3.8
conda activate bibtexcleaner

# Install for usage
pip install --no-cache-dir --force-reinstall git+https://github.com/sciunto-org/python-bibtexparser@main
pip install .
```

## Usage

1. Past your bibtex file content into 'files/references.bib'.
2. Execute `BibTexCleaner`:
    ```python 
    python bibtexcleaner/cleaner.py [use_short]
    ```
    * `use_short`: assumes proceedings to be in short form, loggs a warning if it is not the case.
    * `replace_keys`: replaces the entry keys to match the right format
3. Check `files/remarks.log` to know what has been changed and which fields need further manual adaptions.
4. The cleaned bibtex file can be found at `files/references_cleaned.bib`.

## Cleanup Process

In detail the following changes are made:

### Proceedings

- `title` and `booktitle`:
  - Unnecessary whitespace/linebreaks are removed.
  - Are checked to be equal.
  - The format is checked to be somewhat of this form:
    - `use_short`: `{Proc. of {<ConfAbbrev>}'<YearAbbrev>}`.
    - otherwise: `{Proceedings of the <Conference> ({<ConfAbbrev>}'<YearAbbrev>)}`.
- `key` is rephrased to be `<conference abbreviation><year>`, which is extracted from `title`.
- Every other field except the following is removed: `title`, `booktitle`, `year`, `notes`

### Article / Inproceedings / MISC
- `title`:
  - Unnecessary whitespace/linebreaks are removed.
  - Camel case for words with length > 3.
  - Words with unusual capitalization are surrounded with `{...}`.
- `author`s are rephrased to abbreviate the first name and every intermediate name is removed, e.g., `Albus Percival Wulfric Brian Dumbledore` -> `A. Dumbledore`.
- `journal`
  - In case of an arXiv paper, the entry is adapted to `journal = {arXiv:<some number>}`.
  - In case of an hal paper, the entry is adapted to `journal = {hal-<some number>}`.
- `key` is reset to `<lastname of first author>-<conference or journal abbreviation><year><enumeration>`.
  - In case the journal abbreviation can not be identified, `XXX` is used.
  - In case the year can not be identified, `???` is used.
  - The letter at the end is automatically set based on the already existing entries.
- In case of `inproceedings` the `crossref` is checked: 
  - If there is none, as every information is hardcoded, a warning is logged.
  - If there is no `proceedings` for the given `crossref` a warning is logged. This could be the case if not all information is copied to the `references.bib` file. 
  - If the key of the according `proceedings` has been updated in advance, the `crossref` will be updated, too.
- Every other field except the following is removed: `title`, `author`, `booktitle`, `journal`, `volume`, `number`, `pages`, `editors`, `crossref`, [`year` will be removed if `crossref` is used], `note`

