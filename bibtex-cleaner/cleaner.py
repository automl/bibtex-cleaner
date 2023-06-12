import logging
import os
import re
import string
import sys

import bibtexparser
from bibtexparser.model import Field


class BibTexCleaner:
    
    def __init__(self, file: str, use_short: bool = False, replace_keys: bool = False):
        self.file = file
        self.use_short = use_short
        self.replace_keys = replace_keys
        
        self._setup_logger()
        self._read()
        self._clean_proceedings()
        self._clean_entries()
        self._write()
    
    def _setup_logger(self):
        self.logger = logging.getLogger('bibtext-cleaner')
        self.logger.setLevel(logging.DEBUG)
        
        _file = os.path.join('files', 'remarks.log')
        if os.path.exists(_file):
            os.remove(_file)
        
        file_handler = logging.FileHandler(_file)
        self.logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        self.logger.addHandler(console_handler)
        
    def _read(self):
        self.library = bibtexparser.parse_file(self.file)
        self.logger.info(f"Parsed {len(self.library.blocks)} blocks, including:\n\t{len(self.library.entries)} entries\n\t{len(self.library.comments)} comments\n\t{len(self.library.strings)} strings and\n\t{len(self.library.preambles)} preambles")
        
        if len(self.library.failed_blocks) > 0:
            self.logger.info(f"Some blocks ({len(self.library.failed_blocks)}) failed to parse. Check the entries of 'library.failed_blocks'.")
        
    def _get_proceedings_template(self):
        if self.use_short:
            return"""
            @proceedings{proceedings-key,
                title     = {Proc. of {<ConfAbbrev>}'<YearAbbrev>}, 
                booktitle = {Proc. of {<ConfAbbrev>}'<YearAbbrev>}, 
                year      = {<YearAbbrev>},
            }"""
        return """
            @proceedings{proceedings-key,
                title = {Proceedings of the <Conference> ({<ConfAbbrev>}'<YearAbbrev>)},
                booktitle = {Proceedings of the <Conference> ({<ConfAbbrev>}'<YearAbbrev>)},
                year = {<year>},
            }"""
            
    def _clean_proceedings(self):
        self.proceedings = [entry for entry in self.library.entries if entry.entry_type == 'proceedings']
        self.proceedings_key_updates = dict()

        for entry in self.proceedings:
            self.logger.info(f"\nChecking entry with key '{entry.key}':")
            
            # Rephrase title and booktitle to remove linebreaks
            for field in ['title', 'booktitle']:
                entry.fields_dict[field].value = re.sub(r"\s+", ' ', entry.fields_dict[field].value.replace('\n', ' ')).strip()
            
            # Check that title and booktitle are equal
            if entry.fields_dict['title'].value != entry.fields_dict['booktitle'].value:
                self.logger.info("\tTitle and booktitle are not equal, please rephrase to have them matching.")
                
            # Check that title and booktitle are in the right format
            if self.use_short:
                pattern = r"^Proc\. of \{[a-zA-Z-]+\}(?:/\{[a-zA-Z-]+\})?'\d{2}$"
            else:
                pattern = r"^Proceedings of .+ \(\{[a-zA-Z-]+\}(?:/\{[a-zA-Z-]+\})?'\d{2}\)$"
            if not re.match( pattern, entry.fields_dict['title'].value):
                self.logger.info(f"\tThe title is not in the right format, it is expected to be equivalent to {self._get_proceedings_template()}")
                
            # Rephrase key to: <conference abbreviation><year>
            if self.replace_keys:
                match = re.search(r"\{[a-zA-Z-]+\}(?:/\{[a-zA-Z-]+\})?'\d{2}", entry.fields_dict['title'].value)
                if not match:
                    self.logger.info("\tThe title is not in the right format, it is expected to contain `<ConfAbbrev>'<YearAbbrev>`")
                else:
                    correct_key = re.sub(r'[^a-zA-Z0-9]', '', match.group(0)).lower()
                    if correct_key != entry.key:
                        self.proceedings_key_updates[entry.key] = correct_key
                        entry.key = correct_key
                        self.logger.info(f"\tRephrased key: {entry.key}")
            
            # Remove all fields except the chosen ones, and reorder the fields according to the ordering of the chosen fields
            chosen_fields = ['title', 'booktitle', 'year', 'notes']
            removed_fields = [field.key for field in entry.fields if field.key not in chosen_fields]
            entry.fields = [entry.fields_dict[field] for field in chosen_fields if field in entry.fields_dict]
            if len(removed_fields) > 0:
                self.logger.info(f"\tRemoved fields: {removed_fields}")
            
            self.logger.info("\tDone.")
            
    def _clean_entries(self):
        for e, entry in enumerate([entry for entry in self.library.entries if entry.entry_type != 'proceedings']):
            self.logger.info(f"\nChecking entry with key '{entry.key}':")
            
            # Rephrase title to remove linebreaks
            entry.fields_dict['title'].value = re.sub(r"\s+", ' ', entry.fields_dict['title'].value.replace('\n', ' ')).strip()
            
            # Rephrase title 
            # - to upper case first letter if word length > 3
            # - to surround words with {} if other letters are capitalized than the first one
            title = []
            for w, word in enumerate(entry.fields_dict['title'].value.split(' ')):
                if '{' not in word and '}' not in word:
                    if word[1:].lower() != word[1:] and '-' not in word:
                        if word[-1] == ':':
                            title.append("{" + word[:-1] + "}" + word[-1])
                        else:
                            title.append("{" + word + "}")
                    elif w == 0 or len(word) > 3:
                        title.append(word.capitalize())
                    else:
                        title.append(word)
                else:
                    title.append(word)
            entry.fields_dict['title'].value = ' '.join(title)
            self.logger.info(f"Rephrased title: {entry.fields_dict['title'].value}")
            
            # Rephrase authors: "Albert Einstein and Boris Johnson" -> "A. Einstein and B. Johnson"
            for people in ['editor', 'author']:
                if people in entry.fields_dict and re.match(r'[A-Z]\.\s[A-Za-z-]+(?:\sand\s[A-Z]\.\s[A-Za-z])*', entry.fields_dict[people].value) != entry.fields_dict[people].value:
                    original_peoples = list(person for person in re.sub(r"\s+", ' ', entry.fields_dict[people].value.replace('\n', '')).split(' and '))
                    if len(original_peoples) > 1 or len(original_peoples[0].split(' ')) > 1:
                        peoples = []
                        for original_person in original_peoples:
                            if ',' in original_person:
                                original_person = original_person.split(',')
                                original_person = [original_person[-1].strip(), original_person[0].strip()]
                            else:
                                original_person = original_person.split(' ')
                                for n, name in enumerate(original_person):
                                    if n>0 and '.' in name:
                                        original_person[n] = ''
                                original_person = [x.strip() for x in original_person if x != '']
                            peoples.append(' '.join([f"{original_person[0][0]}.",] + original_person[1:]))
                            
                        entry.fields_dict[people].value = ' and '.join(peoples)
                        self.logger.info(f"\tRephrased {people}: {entry.fields_dict[people].value}")
                
            # Rephrase arXiv papers
            if 'journal' in entry.fields_dict and entry.fields_dict['journal'].value == 'CoRR':
                entry.fields_dict['journal'].value = f"arXiv:{entry.fields_dict['volume'].value.replace('abs/', '')}"
                entry.fields = [field for field in entry.fields if field.key != 'volume']
                self.logger.info(f"\tRephrased journal: {entry.fields_dict['journal'].value}\n\tRemoved volume")
            
            elif 'journal' in entry.fields_dict and 'arxiv' in entry.fields_dict['journal'].value.lower():
                if not re.match(r'arXiv:\d+\.\d+(?:\s\[\w+\])?', entry.fields_dict['journal'].value):
                    for word in entry.fields_dict['journal'].value.split(' '):
                        if ':' in word:
                            break
                    entry.fields_dict['journal'].value = word
                    self.logger.info(f"\tRephrased journal: {entry.fields_dict['journal'].value}")
                
            elif 'eprint' in entry.fields_dict and entry.fields_dict['archivePrefix'].value == 'arXiv':
                entry.fields.append(Field(key='journal', value=f"arXiv:{entry.fields_dict['eprint'].value}"))
                if 'primaryClass' in entry.fields_dict:
                    entry.fields_dict['journal'].value += f" [{entry.fields_dict['primaryClass'].value}]"
                entry.fields = [field for field in entry.fields if field.key not in ['eprint', 'archivePrefix', 'primaryClass']]
                self.logger.info(f"\tRephrased journal: {entry.fields_dict['journal'].value}\n\tRemoved eprint, archivePrefix, primaryClass")
                
            # Rephrase HAL papers
            if 'journal' in entry.fields_dict and 'hal' in entry.fields_dict['journal'].value:
                for word in entry.fields_dict['journal'].value.split(' '):
                    if '-' in word:
                        break
                entry.fields_dict['journal'].value = word
                self.logger.info(f"\tRephrased journal: {entry.fields_dict['journal'].value}")
                
            # Reset key to: <lastname of first author>-<conference or journal abbreviation><year><enumeration>
            peoples = entry.fields_dict['author'].value if 'author' in entry.fields_dict else entry.fields_dict['editor'].value
            first_author = peoples.split(' and ')[0].split(' ')[-1]
            
            # replace all letters from first_author that are none alphabetic
            if self.replace_keys:
                first_author = re.sub(r'[^a-zA-Z]', '', first_author)
                
                published = ''
                if 'journal' in entry.fields_dict:
                    published = entry.fields_dict['journal'].value.split(':')[0] 
                elif 'crossref' in entry.fields_dict:
                    published = entry.fields_dict['crossref'].value
                else:
                    published = 'XXX'
                published = re.sub(r'[^a-zA-Z]', '', published)
                
                year = ''
                if 'crossref' in entry.fields_dict:
                    # Check if crossref has to be updated due to changed key of proceeding
                    if entry.fields_dict['crossref'].value in self.proceedings_key_updates:
                        self.logger.info(f"\tCrossref has been updated from '{entry.fields_dict['crossref'].value}' to '{self.proceedings_key_updates[entry.fields_dict['crossref'].value]}' due to an update of the according proceedings key.")
                        entry.fields_dict['crossref'].value = self.proceedings_key_updates[entry.fields_dict['crossref'].value]
                    
                    # Check crossref exists
                    if entry.fields_dict['crossref'].value not in [proceeding.key for proceeding in self.proceedings]:
                        self.logger.info(f"\tCrossref {entry.fields_dict['crossref'].value} not found in proceedings. Please add it according to the template:{self._get_proceedings_template()}")
                    year = entry.fields_dict['crossref'].value[-2:]
                
                else:
                    if 'year' in entry.fields_dict:
                        year = entry.fields_dict['year'].value[-2:] 
                    else:
                        year = ''
                
                correct_key = f"{first_author}-{published}{year}".lower()
                
                if not entry.key.startswith(correct_key):
                    same_keys = sorted([i.key for i in self.library.entries if i.key.startswith(correct_key) and i.key != entry.key])
                    correct_key += chr(ord(same_keys[-1][-1])+1) if len(same_keys)>0 else 'a'
                
                    entry.key = correct_key
                    self.logger.info(f"\tRephrased key: {entry.key}")
            
            # Check if proceeding has been extracted and used via crossref
            if entry.entry_type == 'inproceedings' and 'booktitle' in entry.fields_dict:
                self.logger.info(f"\tProceeding '{entry.fields_dict['booktitle'].value}' is hardcoded. Please extract it according to the template:{self._get_proceedings_template()}")
            
            # Remove all fields except the chosen ones, and reorder the fields according to the ordering of the chosen fields
            chosen_fields = ['title', 'author', 'editor', 'booktitle', 'crossref', 'journal', 'volume', 'number', 'pages', 'year', 'note']
            if 'crossref' in entry.fields_dict:
                chosen_fields = [f for f in chosen_fields if f not in ['year', 'booktitle', 'journal']]
            removed_fields = [field.key for field in entry.fields if field.key not in chosen_fields]
            entry.fields = [entry.fields_dict[field] for field in chosen_fields if field in entry.fields_dict] # TODO remove year if crossref
            if len(removed_fields) > 0:
                self.logger.info(f"\tRemoved fields: {removed_fields}")
                
            self.logger.info("\tDone.")
                
        
    def _write(self):
        bibtexparser.write_file(self.file.split(".")[0] + "_cleaned.bib", self.library)
            

if __name__ == '__main__':
    nargs = len(sys.argv)
    BibTexCleaner('files/references.bib', use_short='use_short' in sys.argv, replace_keys='replace_keys' in sys.argv)
