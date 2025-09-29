# HTML2TEI

Map the HTML schema of portals to valid [TEI XML](https://tei-c.org/) with the tags and structures used in them using
 small manual portal-specific configurations.

The portal-specific configuration is created manually with the help of three different tools which aid evaluating
 the inventory of the tags and structures used in the HTML code. The manual evaluation of such structures
 enables one to create a valid TEI XML from the HTML source keeping all desired (text) schema elements
 in a fine-grained way carefully supervised by the user. In addition to converting the article body,
 the metadata can be converted to the [Schema.org](https://schema.org/) standard.

The conversion process is automatic and scales well on large portals with the same schema

## Requirements

- Python 3.8+
- For Newspaper3k, the installation of the following packages must precede the installation of this program:
  `python3-dev libxml2-dev libxslt-dev libjpeg-dev zlib1g-dev libpng12-dev`

## Install

### pip

`pip3 install html2tei`

The following extras can be installed:

- Newspaper3k: `newspaper`
- JusText: `justext`
- All the above: `full`

E.g. `pip3 install html2tei[full]`

### Manual

[_Poetry_](https://python-poetry.org/) and (optionally) [_GNU Make_](https://www.gnu.org/software/make/) are required.

1. `git clone https://github.com/ELTE-DH/HTML2TEI.git`
2. Run `make`

On Windows or without Make (after cloning the repository):

1. `poetry install --no-root`
2. `poetry build`
3. `poetry run pip install --upgrade dist/*.whl` (the correct filename must be specified on Windows)

To install extras run: `poetry install -E [NAME OF THE EXTRA TO INSTALL]`

## Usage

This program is designed to be used with [WebArticleCurator](https://github.com/elte-dh/WebArticleCurator/) (WAC).
The article WARC files (created with the WAC) should be placed in a directory (`warc-dir`) and a configuration YAML must
 map the WARC files to the specific portal configuration (`warcfilename: configdirectoryname`).
The program can be run from command line or from the Python API see the details below. 

### Modes

There are five modes of the program:

- Create _HTML Content Tree_ (`content-tree`): Read the whole warc file to summarize all the structures that occur
  in the portal schema. Finally, the accumulated information represents the aggregated tree structure of all articles 
  from the portal as a nested YAML dictionary
  (for manual inspection)
- The _Tag Inventory Maker_ (`inventory-maker`): Create a _text_ and _notext_ tag table from all articles within a warc
  file with their gathered information (it will be the basis for manual configuration of renaming unique tag occurances 
  in order to translate them to TEI-XML format)
- The _Tag Bigrams Maker_ (`bigram-maker`): Create the bigram tag table from the articles with their
  gathered information (this table is an add-on that can be used to map the schema)
- The _Portal Article Cleaner_ (`cleaner`): Create the TEI XMLs from the site-specific configuration and
  from the tables supplemented with new, manually created label names
- _Diff Tag Tables_ (`diff-tables`): Compare and update the generated (and modified) tables if there are new data
  for the same portal

### Command Line Arguments 

#### Common Arguments

- `-i`, `--input-config`: WARC filename to portal name mapping in YAML
- `-c`, `--configs-dir`: The directory for portal-specific configs
- `-l`, `--log-dir`: The directory for putting logs
- `-w`, `--warc-dir`: The directory to read WARCs from
- `-o`, `--output-dir`: The directory to put output files
- `-L`, `--log-level`: Log verbosity level (default: INFO)'

The files and directories must present. All arguments except `log-level` are mandatory for the following four modes

#### HTML Content Tree (`content-tree`)

- `-t`, `--task-name`: The name of the task to appear in the logs (default: HTML Content Tree)

#### Tag Inventory Maker (`inventory-maker`)

- `-t`, `--task-name`: The name of the task to appear in the logs (default: Tag Inventory Maker)
- `-r`, `--recursive`: Use just direct descendants or all (default: True)

#### Tag Bigrams Maker (`bigram-maker`)

- `-t`, `--task-name`: The name of the task to appear in the logs (default: Tag Bigrams Maker)
- `-r`, `--recursive`: Use just direct descendants or all (default: True)

#### Portal Article Cleaner (`cleaner`)

- `-m`, `--write-out-mode`: The schema removal tool to use (ELTEDH, JusText, Newspaper3k) (default: eltedh)
- `-t`, `--task-name`: The name of the task to appear in the logs (default: Portal Article Cleaner)
- `-O`, `--output-debug`: Normal output generation (validate-hash-compress and UUID file names) or print into
  the output directory without validation using human-friendly names (default: False, normal output)
- `-p`, `--run-parallel`: Run processing in parallel or all operation must be used sequentially
  (default: True, parallel)
- `-d`, `--with-specific-dicts`: Load portal-specific dictionaries (tables) (default: True)
- `-b`, `--with-specific-base-tei`: Load portal-specific base TEI XML (default: True)

#### Diff Tag Tables (`diff-tables`)

- `--diff-dir`: The directory which contains the directories
- `--old-filename`: The filename for the old table 
- `--new-filename`: The filename for the new table
- `--merge-filename`: The filename for the merged table

### Python API

#### Helper functions for the Configs

- `parse_date(date_raw, date_format, locale='hu_HU.UTF-8')`: Parse date according to the parameters
  (locale and date format) 
- `BASIC_LINK_ATTRS`: A basic list of html tags that contain attributes to preserve. It can be overwritten based on
  the set of the given portal
- `decompose_listed_subtrees_and_mark_media_descendants(article_dec, decomp, media_list)`: 
  Mark the lower level of the media blocks and delete tags to be deleted
- `tei_defaultdict(mandatory_keys=('sch:url', 'sch:name'), missing_value=None)`:
  Create a defaultdict preinitialized with the mandatory Schema.org keys set to default

# For the Main Python API

- `run_main(warc_filename, configs_dir, log_dir, warc_dir, output_dir, init_portal_fun,
            run_params=None, logfile_level='INFO', console_level='INFO')`: Main runner function
- `WRITE_OUT_MODES`: A dictionary to add custom write-out modes when needed
- `diff_all_tag_table(diff_dir, old_filename, new_filename, out_filename)`: The main function to update tables
- `tag_bigrams_init_portal(log_dir, output_dir, run_params, portal_name, tei_logger, warc_level_params,
                           rest_config_params)`: The portal initator function as called from CLI argument
- `content_tree_init_portal(log_dir, output_dir, run_params, portal_name, tei_logger, warc_level_params,
                            rest_config_params)`: The portal initator function as called from CLI argument
- `tag_inventory_init_portal(log_dir, output_dir, run_params, portal_name, tei_logger, warc_level_params,
                             rest_config_params)`: The portal initator function as called from CLI argument
- `portal_article_cleaner_init_portal(log_dir, output_dir, run_params, portal_name, tei_logger, warc_level_params,
                                      rest_config_params)`: The portal initator function as called from CLI argument

# For the Low-level API: Defining Custom Modes

- `init_output_writer(output_dir, portal_name, output_debug, tei_logger)`: Initialises the class for writing output
  (into a zipfile or a directory)
- `create_new_tag_with_string(beauty_xml, tag_string, tag_name, append_to=None)`: Helper function to create
  a new XML tag containing string in it. If provided append the newly created tag to a parent tag
- `immediate_text(tag)`: Count the number of words (non-whitespace text) immediately under
  the parameter tag excluding comments
- `to_friendly(ch, excluded_tags_fun)`: Convert tag name and sorted attributes to string in order to use it later
  (e.g. tag_freezer in the tables)
- `run_single_process(warc_filename, file_names_and_modes, main_function, sub_functions, after_function, after_params)`:
  Read a WARC file and sequentially process all articles in it with main_function (multi-page articles are handled
  as one entry) and yield the result after filtered through `after_function`
- `run_multiple_process(warc_filename, file_names_and_modes, main_function, sub_functions, after_function,
  after_params)`: Read a WARC file and sequentially process all articles in it with main_function in parallel preserving
  ordering (multi-page articles are handled as one entry) and yield the result after filtered through `after_function`
- `dummy_fun(*_)`: A function always returns None no matter how many arguments were given
- `process_article`: A generic article processing skeleton used by multiple targets

# Licence

This project is licensed under the terms of the GNU LGPL 3.0 license.

# References

The DOI of the code is: TODO

If you use this program, please cite the following paper:

[__The ELTE.DH Pilot Corpus – Creating a Handcrafted Gigaword Web Corpus with Metadata__ Balázs Indig, Árpád Knap, 
Zsófia Sárközi-Lindner, Mária Timári, Gábor Palkó _In the Proceedings of the 12th Web as Corpus Workshop (WAC XII)_,
pages 33-41 Marseille, France 2020](https://www.aclweb.org/anthology/2020.wac-1.5.pdf)

```
@inproceedings{indig-etal-2020-elte,
    title = "The {ELTE}.{DH} Pilot Corpus {--} Creating a Handcrafted {G}igaword Web Corpus with Metadata",
    author = {Indig, Bal{\'a}zs  and
      Knap, {\'A}rp{\'a}d  and
      S{\'a}rk{\"o}zi-Lindner, Zs{\'o}fia  and
      Tim{\'a}ri, M{\'a}ria  and
      Palk{\'o}, G{\'a}bor},
    booktitle = "Proceedings of the 12th Web as Corpus Workshop",
    month = may,
    year = "2020",
    address = "Marseille, France",
    publisher = "European Language Resources Association",
    url = "https://www.aclweb.org/anthology/2020.wac-1.5",
    pages = "33--41",
    abstract = "In this article, we present the method we used to create a middle-sized corpus using
     targeted web crawling. Our corpus contains news portal articles along with their metadata, that can be useful
     for diverse audiences, ranging from digital humanists to NLP users. The method presented in this paper applies
     rule-based components that allow the curation of the text and the metadata content. The curated data can thereon
     serve as a reference for various tasks and measurements. We designed our workflow to encourage modification and
     customisation. Our concept can also be applied to other genres of portals by using the discovered patterns
     in the architecture of the portals. We found that for a systematic creation or extension of a similar corpus,
     our method provides superior accuracy and ease of use compared to The Wayback Machine, while requiring minimal
     manpower and computational resources. Reproducing the corpus is possible if changes are introduced
     to the text-extraction process. The standard TEI format and Schema.org encoded metadata is used
     for the output format, but we stress that placing the corpus in a digital repository system is recommended
     in order to be able to define semantic relations between the segments and to add rich annotation.",
    language = "English",
    ISBN = "979-10-95546-68-9",
}
```

# Acknowledgements

The authors acknowledge the support of the National Laboratory for Digital
Heritage. Project no. 2022-2.1.1-NL-2022-00009 has been implemented with the
support provided by the Ministry of Culture and Innovation of Hungary from the
National Research, Development and Innovation Fund, financed under the
2022-2.1.1-NL funding scheme.
