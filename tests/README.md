# Input and Output files go here

- `input/` directory should contain input files (FILE1.tsv, FILE2.tsv)
- `gold/` directory should contain the corresponding gold standard files (FILE1.tsv, FILE2.tsv)

The tests give all files in the `input/` directory separately as parameter (e.g. `FILENAME.tsv`) and
expect the same output as the file with the same name in the `gold/` directory (in this case `FILENAME.tsv`).
