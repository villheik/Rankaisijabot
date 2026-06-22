import pytest
from bot.cogs.poe import PoeBuild, CLASSES, SKILLS, _ALL_SKILLS


class TestParseArgs:
    def test_empty_returns_all_none(self):
        assert PoeBuild._parse_args("") == (False, None, None, None)

    def test_phrecia_keyword(self):
        use_phrecia, cls, asc, cat = PoeBuild._parse_args("phrecia")
        assert use_phrecia is True
        assert cls is None
        assert asc is None
        assert cat is None

    def test_class_name(self):
        _, cls, asc, _ = PoeBuild._parse_args("witch")
        assert cls == "Witch"
        assert asc is None

    def test_class_with_category(self):
        _, cls, asc, cat = PoeBuild._parse_args("witch minion")
        assert cls == "Witch"
        assert asc is None
        assert cat == "minion"

    def test_phrecia_class_category(self):
        use_phrecia, cls, asc, cat = PoeBuild._parse_args("phrecia witch minion")
        assert use_phrecia is True
        assert cls == "Witch"
        assert asc is None
        assert cat == "minion"

    def test_standard_ascendancy(self):
        use_phrecia, cls, asc, _ = PoeBuild._parse_args("slayer")
        assert use_phrecia is False
        assert cls == "Duelist"
        assert asc == "Slayer"

    def test_phrecia_ascendancy_auto_detects_league(self):
        use_phrecia, cls, asc, _ = PoeBuild._parse_args("herald")
        assert use_phrecia is True
        assert cls == "Witch"
        assert asc == "Herald"

    def test_phrecia_multiword_ascendancy(self):
        use_phrecia, cls, asc, _ = PoeBuild._parse_args("bog shaman")
        assert use_phrecia is True
        assert cls == "Witch"
        assert asc == "Bog Shaman"

    def test_phrecia_multiword_ascendancy_with_keyword(self):
        use_phrecia, cls, asc, _ = PoeBuild._parse_args("phrecia ancestral commander")
        assert use_phrecia is True
        assert cls == "Marauder"
        assert asc == "Ancestral Commander"

    def test_phrecia_ascendancy_without_keyword(self):
        use_phrecia, cls, asc, _ = PoeBuild._parse_args("surfcaster")
        assert use_phrecia is True
        assert cls == "Shadow"
        assert asc == "Surfcaster"

    def test_category_spell(self):
        _, cls, asc, cat = PoeBuild._parse_args("spell")
        assert cls is None
        assert asc is None
        assert cat == "spell"

    def test_category_caster_alias(self):
        _, _, _, cat = PoeBuild._parse_args("caster")
        assert cat == "spell"

    def test_category_summoner_alias(self):
        _, _, _, cat = PoeBuild._parse_args("summoner")
        assert cat == "minion"

    def test_category_trap(self):
        _, _, _, cat = PoeBuild._parse_args("trap")
        assert cat == "trap"

    def test_category_mine_alias(self):
        _, _, _, cat = PoeBuild._parse_args("mine")
        assert cat == "trap"

    def test_category_range(self):
        _, _, _, cat = PoeBuild._parse_args("range")
        assert cat == "range"

    def test_category_ranged_alias(self):
        _, _, _, cat = PoeBuild._parse_args("ranged")
        assert cat == "range"

    def test_phrecia_with_class_and_asc(self):
        use_phrecia, cls, asc, _ = PoeBuild._parse_args("phrecia harbinger")
        assert use_phrecia is True
        assert cls == "Witch"
        assert asc == "Harbinger"

    def test_standard_asc_with_phrecia_keyword_ignores_standard_asc(self):
        # "phrecia slayer" — slayer is standard, phrecia league active;
        # no phrecia asc named → asc stays None, class picked from "slayer"? No —
        # with phrecia active we only scan phrecia ascs, "slayer" won't match any.
        # Class scan also won't match "slayer" as a class name.
        use_phrecia, cls, asc, _ = PoeBuild._parse_args("phrecia slayer")
        assert use_phrecia is True
        assert asc is None
        assert cls is None


class TestGenerateBuild:
    def _generate(self, use_phrecia, chosen_class, chosen_asc, chosen_category):
        """Replicate the command's generation logic for testing."""
        import random
        if chosen_class is None:
            chosen_class = random.choice(list(CLASSES.keys()))
        league = "phrecia" if use_phrecia else "standard"
        if chosen_asc is None:
            chosen_asc = random.choice(CLASSES[chosen_class][league])
        skill_pool = SKILLS[chosen_category] if chosen_category else _ALL_SKILLS
        chosen_skill = random.choice(skill_pool)
        return chosen_class, chosen_asc, chosen_skill

    def test_output_class_in_classes(self):
        cls, asc, skill = self._generate(False, None, None, None)
        assert cls in CLASSES

    def test_output_standard_asc_valid(self):
        cls, asc, skill = self._generate(False, "Witch", None, None)
        assert asc in CLASSES["Witch"]["standard"]

    def test_output_phrecia_asc_valid(self):
        cls, asc, skill = self._generate(True, "Witch", None, None)
        assert asc in CLASSES["Witch"]["phrecia"]

    def test_output_skill_in_category(self):
        cls, asc, skill = self._generate(False, None, None, "minion")
        assert skill in SKILLS["minion"]

    def test_fixed_asc_preserved(self):
        cls, asc, skill = self._generate(False, "Duelist", "Slayer", None)
        assert cls == "Duelist"
        assert asc == "Slayer"

    def test_skill_in_all_skills_when_no_category(self):
        cls, asc, skill = self._generate(False, None, None, None)
        assert skill in _ALL_SKILLS
