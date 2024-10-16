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
import unittest

import yaml

from wilhelm_python_sdk.vocabulary_parser import GERMAN
from wilhelm_python_sdk.vocabulary_parser import get_attributes
from wilhelm_python_sdk.vocabulary_parser import get_definitions
from wilhelm_python_sdk.vocabulary_parser import get_inferred_declension_links
from wilhelm_python_sdk.vocabulary_parser import get_inferred_links
from wilhelm_python_sdk.vocabulary_parser import \
    get_inferred_tokenization_links

UNKOWN_DECLENSION_NOUN_YAML = """
    term: die Grilltomate
    definition: the grilled tomato
    declension: Unknown
"""

HUT_YAML = """
    term: der Hut
    definition: the hat
    declension:
      - ["",         singular,      plural]
      - [nominative, Hut,           Hüte  ]
      - [genitive,   "Hutes, Huts", Hüte  ]
      - [dative,     Hut,           Hüten ]
      - [accusative, Hut,           Hüte  ]
"""

HUT_DECLENSION_MAP = {
    "declension-0-0": "",
    "declension-0-1": "singular",
    "declension-0-2": "plural",

    "declension-1-0": "nominative",
    "declension-1-1": "Hut",
    "declension-1-2": "Hüte",

    "declension-2-0": "genitive",
    "declension-2-1": "Hutes, Huts",
    "declension-2-2": "Hüte",

    "declension-3-0": "dative",
    "declension-3-1": "Hut",
    "declension-3-2": "Hüten",

    "declension-4-0": "accusative",
    "declension-4-1": "Hut",
    "declension-4-2": "Hüte",
}


class TestLoader(unittest.TestCase):

    def test_get_definitions(self):
        self.assertEqual(
            [("adj.", "same"), ("adv.", "namely"), (None, "because")],
            get_definitions({
                "definition": ["(adj.) same", "(adv.) namely", "because"]
            }),
        )

    def test_single_definition_term(self):
        self.assertEqual(
            [(None, "one")],
            get_definitions({
                "definition": "one"
            }),
        )

    def test_numerical_definition(self):
        self.assertEqual(
            [(None, "1")],
            get_definitions({
                "definition": 1
            }),
        )

    def test_missing_definition(self):
        with self.assertRaises(ValueError):
            get_definitions({"defintion": "I'm 23 years old."})

    def test_get_attributes(self):
        self.assertEqual(
            {"name": "der Hut", "language": "German"} | HUT_DECLENSION_MAP,
            get_attributes(yaml.safe_load(HUT_YAML), GERMAN, "name"),
        )

    def test_get_inferred_links_on_unrelated_terms(self):
        vocabulary = yaml.safe_load("""
            vocabulary:
              - term: der Beruf
                definition: job
                declension:
                  - ["",         singular,          plural ]
                  - [nominative, Beruf,             Berufe ]
                  - [genitive,   "Berufes, Berufs", Berufe ]
                  - [dative,     Beruf,             Berufen]
                  - [accusative, Beruf,             Berufe ]
              - term: der Qualitätswein
                definition: The vintage wine
                declension:
                  - ["",         singular,                          plural         ]
                  - [nominative, Qualitätswein,                     Qualitätsweine ]
                  - [genitive,   "Qualitätsweines, Qualitätsweins", Qualitätsweine ]
                  - [dative,     Qualitätswein,                     Qualitätsweinen]
                  - [accusative, Qualitätswein,                     Qualitätsweine ]
        """)["vocabulary"]
        label_key = "name"

        self.assertEqual(
            [],
            get_inferred_links(vocabulary, label_key)
        )

    def test_get_inferred_declension_links(self):
        DER_REIS = """
            term: der Reis
            definition: the rice
            declension:
              - ["",         singular, plural]
              - [nominative, Reis,     Reise ]
              - [genitive,   Reises,   Reise ]
              - [dative,     Reis,     Reisen]
              - [accusative, Reis,     Reise ]
        """
        DIE_REISE = """
            term: die Reise
            definition: the travel
            declension:
              - ["",         singular, plural]
              - [nominative, Reise,    Reisen]
              - [genitive,   Reise,    Reisen]
              - [dative,     Reise,    Reisen]
              - [accusative, Reise,    Reisen]
        """

        vocabulary = [yaml.safe_load(DER_REIS), yaml.safe_load(DIE_REISE)]
        label_key = "name"

        self.assertEqual(
            [
                {
                    "source_label": "der Reis",
                    "target_label": "die Reise",
                    "attributes": {label_key: "sharing declensions"}
                }
            ],
            get_inferred_declension_links(vocabulary, label_key)
        )

    def test_get_inferred_tokenization_links(self):
        vocabulary = yaml.safe_load("""
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
              - term: letzte
                definition: (adj.) last
              - term: in den letzten Jahren
                definition: in recent years
        """)["vocabulary"]
        label_key = "name"

        self.assertEqual(
            [
                {
                    'attributes': {'name': 'term related'},
                    'source_label': 'seit zwei Jahren',
                    'target_label': 'das Jahr'
                },
                {
                    'attributes': {'name': 'term related'},
                    'source_label': 'seit zwei Jahren',
                    'target_label': 'in den letzten Jahren'
                },
                {
                    'attributes': {'name': 'term related'},
                    'source_label': 'in den letzten Jahren',
                    'target_label': 'das Jahr'
                },
                {
                    'attributes': {'name': 'term related'},
                    'source_label': 'in den letzten Jahren',
                    'target_label': 'seit zwei Jahren'
                }
            ],
            get_inferred_tokenization_links(vocabulary, label_key)
        )
