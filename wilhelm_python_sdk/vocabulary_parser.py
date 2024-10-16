# Copyright Jiaqi Liu
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import re

import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GERMAN = "German"
LATIN = "Latin"
ANCIENT_GREEK = "Ancient Greek"

EXCLUDED_DECLENSION_ENTRIES = [
    "",
    "singular",
    "plural",
    "masculine",
    "feminine",
    "neuter",
    "nominative",
    "genitive",
    "dative",
    "accusative",
    "N/A"
]
EXCLUDED_TOKENS = ["der", "die", "das"]


def get_vocabulary(yaml_path: str) -> list:
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)["vocabulary"]


def get_definitions(word) -> list[(str, str)]:
    """
    Extract definitions from a word as a list of bi-tuples, with the first element being the predicate and the second
    being the definition.

    For example::

    definition:
      - term: nämlich
        definition:
          - (adj.) same
          - (adv.) namely
          - because

    The method will return `[("adj.", "same"), ("adv.", "namely"), (None, "because")]`

    The method works for the single-definition case, i.e.::

    definition:
      - term: na klar
        definition:

    returns a list of one tupple `[(None, "of course")]`

    Note that any definition are converted to string. If the word does not contain a field named exactly "definition", a
    ValueError is raised.

    :param word:  A dictionary that contains a "definition" key whose value is either a single-value or a list of
                  single-values
    :return: a list of two-element tuples, where the first element being the predicate (can be `None`) and the second
             being the definition
    """
    logging.info("Extracting definitions from {}".format(word))

    if "definition" not in word:
        raise ValueError("{} does not contain 'definition' field. Maybe there is a typo".format(word))

    predicate_with_definition = []

    definitions = [word["definition"]] if not isinstance(word["definition"], list) else word["definition"]

    for definition in definitions:
        definition = str(definition)

        definition = definition.strip()

        match = re.match(r"\((.*?)\)", definition)
        if match:
            predicate_with_definition.append((match.group(1), re.sub(r'\(.*?\)', '', definition).strip()))
        else:
            predicate_with_definition.append((None, definition))

    return predicate_with_definition


def get_declension_attributes(word: object) -> dict[str, str]:
    """
    Returns the declension of a word.

    If the word does not have a "declension" field, the function returns an empty dictionary.

    If the noun's declension is, for some reasons, "Unknown", this function will return an empty dict. Otherwise, the
    declension table is flattened like with row-col index in the map key::

    "declension-0-0": "",
    "declension-0-1": "singular",
    "declension-0-2": "singular",
    "declension-0-3": "singular",
    "declension-0-4": "plural",
    "declension-0-5": "plural",

    :param word:  A vocabulary represented in YAML dictionary which has a "declension" key

    :return: a flat map containing all the YAML encoded information about the noun excluding term and definition
    """

    if "declension" not in word:
        return {}

    declension = word["declension"]

    if declension == "Unknown":
        return {}

    attributes = {}
    for i, row in enumerate(declension):
        for j, col in enumerate(row):
            attributes[f"declension-{i}-{j}"] = declension[i][j]

    return attributes


def get_attributes(word: object, language: str, node_label_property_key: str) -> dict[str, str]:
    """
    Returns a flat map as the Term node properties stored in Neo4J.

    :param word:  A German vocabulary representing

    :return: a flat map containing all the YAML encoded information about the vocabulary
    """
    return {node_label_property_key: word["term"], "language": language} | get_declension_attributes(word)


def get_inferred_links(vocabulary: list[dict], label_key: str) -> list[dict]:
    """
    Return a list of inferred links between related vocabularies.

    This function is the point of extending link inference capabilities. At this point, the link inference includes

    - :py:meth:`declension sharing <wilhelm_python_sdk.vocabulary_parser.get_inferred_declension_links>`
    - :py:meth:`token sharing <wilhelm_python_sdk.vocabulary_parser.get_inferred_tokenization_links>`

    :param vocabulary:  A wilhelm-vocabulary repo YAML file deserialized
    :param label_key:  The name of the node attribute that will be used as the label in displaying the node

    :return: a list of link object, each of which has a "source_label", a "target_label", and an "attributes" key
    """
    return (get_inferred_declension_links(vocabulary, label_key) +
            get_inferred_tokenization_links(vocabulary, label_key))


def get_inferred_declension_links(vocabulary: list[dict], label_key: str) -> list[dict]:
    """
    Return a list of inferred links between related vocabulary terms that share declension table entries

    This mapping will be used to create more links in graph database.

    The operation calling this method was inspired by the spotting the relationship between "die Reise" and "der Reis"
    who share large portions of their declension table. In this case, there will be a link between "die Reise" and
    "der Reis". Linking the vocabulary this way helps memorize vocabulary more efficiently

    :param vocabulary:  A wilhelm-vocabulary repo YAML file deserialized
    :param label_key:  The name of the node attribute that will be used as the label in displaying the node

    :return: a list of link object, each of which has a "source_label", a "target_label", and an "attributes" key
    """
    link_hints = {}
    for word in vocabulary:
        for key, value in get_declension_attributes(word).items():
            if value not in EXCLUDED_DECLENSION_ENTRIES:
                for declension in value.split(","):
                    link_hints[declension.strip()] = word["term"]

    inferred_links = []
    for word in vocabulary:
        term = word["term"]
        attributes = get_attributes(word, GERMAN, label_key)

        for attribute_value in attributes.values():
            if (attribute_value in link_hints) and (term != link_hints[attribute_value]):
                inferred_links.append({
                    "source_label": term,
                    "target_label": link_hints[attribute_value],
                    "attributes": {label_key: "sharing declensions"},
                })
                break

    return inferred_links


def get_inferred_tokenization_links(vocabulary: list[dict], label_key: str) -> list[dict]:
    """
    Return a list of inferred links between related vocabulary terms which are related to one another.

    This mapping will be used to create more links in graph database.

    This was inspired by the spotting the relationships among::

        vocabulary:
          - term: das Jahr
            definition: the year
            declension:
              - ["",         singular,        plural        ]
              - [nominative, Jahr,            "Jahre, Jahr" ]
              - [genitive,   "Jahres, Jahrs", "Jahre, Jahr" ]
              - [dative,     Jahr,            "Jahren, Jahr"]
              - [accusative, Jahr,            "Jahre, Jahr" ]
          - term: seit zwei Jahren
            definition: for two years
          - term: in den letzten Jahren
            definition: in recent years

    1. Both 2nd and 3rd are related to the 1st and the two links can be inferred by observing that "Jahren" in 2nd and
       3rd match the declension table of the 1st
    2. In addition, the 2nd and 3rd are related because they both have "Jahren".

    Given the 2 observations above, this function tokenizes the "term" and the declension table of each word. If two
    words share at least 1 token, they are defined to be "related"

    :param vocabulary:  A wilhelm-vocabulary repo YAML file deserialized
    :param label_key:  The name of the node attribute that will be used as the label in displaying the node

    :return: a list of link object, each of which has a "source_label", a "target_label", and an "attributes" key
    """
    tokenization = {}
    for word in vocabulary:
        term = word["term"]
        tokenization[term] = set()

        # declension tokenization
        for key, value in get_declension_attributes(word).items():
            if value not in EXCLUDED_DECLENSION_ENTRIES:
                for declension in value.split(","):
                    cleansed = declension.lower().strip()
                    tokenization[term].add(cleansed)

        # term tokenization
        for token in term.split(" "):
            cleansed = token.lower().strip()
            if cleansed not in EXCLUDED_TOKENS:
                tokenization[term].add(cleansed)

    inferred_links = []
    for word in vocabulary:
        this_term = word["term"]

        for that_term, that_term_tokens in tokenization.items():
            jump_to_next_term = False

            if this_term == that_term:
                continue

            for this_token in this_term.split(" "):
                for that_token in that_term_tokens:
                    if this_token.lower().strip() == that_token:
                        inferred_links.append({
                            "source_label": this_term,
                            "target_label": that_term,
                            "attributes": {label_key: "term related"},
                        })
                        jump_to_next_term = True
                        break

                if jump_to_next_term:
                    break

    return inferred_links
