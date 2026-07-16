import random
from typing import Optional
from discord.ext import commands

CLASSES: dict[str, dict[str, list[str]]] = {
    "Duelist": {
        "standard": ["Slayer", "Gladiator", "Champion"],
        "phrecia": ["Aristocrat", "Gambler", "Paladin"],
    },
    "Marauder": {
        "standard": ["Juggernaut", "Berserker", "Chieftain"],
        "phrecia": ["Ancestral Commander", "Behemoth", "Antiquarian"],
    },
    "Ranger": {
        "standard": ["Deadeye", "Raider", "Pathfinder"],
        "phrecia": ["Wildspeaker", "Whisperer", "Daughter of Oshabi"],
    },
    "Scion": {
        "standard": ["Ascendant"],
        "phrecia": ["Scavenger"],
    },
    "Shadow": {
        "standard": ["Assassin", "Saboteur", "Trickster"],
        "phrecia": ["Servant of Arakaali", "Blind Prophet", "Surfcaster"],
    },
    "Templar": {
        "standard": ["Inquisitor", "Hierophant", "Guardian"],
        "phrecia": ["Architect of Chaos", "Puppeteer", "Polytheist"],
    },
    "Witch": {
        "standard": ["Necromancer", "Elementalist", "Occultist"],
        "phrecia": ["Harbinger", "Herald", "Bog Shaman"],
    },
}

SKILLS: dict[str, list[str]] = {
    "melee": [
        "Bladestorm", "Boneshatter", "Cleave", "Consecrated Path", "Corrupting Fever",
        "Cyclone", "Double Strike", "Dual Strike", "Earthquake", "Elemental Hit",
        "Flicker Strike", "Frost Blades", "Glacial Hammer", "Ground Slam",
        "Heavy Strike", "Holy Strike", "Ice Crash", "Infernal Blow",
        "Lacerate", "Lightning Strike", "Molten Strike", "Perforate",
        "Rage Vortex", "Reap", "Reave", "Shield Crush", "Shield Charge",
        "Smite", "Static Strike", "Sunder", "Tectonic Slam", "Viper Strike",
        "Volcanic Fissure", "Whirling Blades", "Wild Strike",
    ],
    "range": [
        "Barrage", "Burning Arrow", "Caustic Arrow", "Cobra Lash",
        "Explosive Arrow", "Galvanic Arrow", "Ice Shot", "Kinetic Blast",
        "Kinetic Bolt", "Lancing Steel", "Lightning Arrow", "Poisonous Concoction",
        "Puncture", "Rain of Arrows", "Scourge Arrow", "Shattering Steel",
        "Spectral Shield Throw", "Spectral Throw", "Split Arrow",
        "Splitting Steel", "Tornado Shot", "Toxic Rain", "Venom Gyre",
    ],
    "spell": [
        "Arc", "Armageddon Brand", "Ball Lightning", "Blade Vortex",
        "Blazing Salvo", "Blight", "Bodyswap", "Crackling Lance",
        "Creeping Frost", "Divine Ire", "Essence Drain",
        "Exsanguinate", "Fireball", "Firestorm", "Flame Surge",
        "Freezing Pulse", "Frostbolt", "Hexblast", "Ice Nova", "Ice Spear",
        "Incinerate", "Lightning Tendrils", "Penance Brand",
        "Purifying Flame", "Righteous Fire", "Rolling Magma", "Scorching Ray",
        "Bane", "Blade Blast", "Bladefall", "Cold Snap", "Contagion",
        "Dark Pact", "Discharge", "Ethereal Knives", "Eye of Winter",
        "Flameblast", "Forbidden Rite", "Glacial Cascade", "Hydrosphere",
        "Lightning Conduit", "Orb of Storms", "Shock Nova", "Soulrend",
        "Spark", "Storm Brand", "Storm Burst", "Storm Call",
        "Void Sphere", "Voltaxic Burst", "Vortex", "Wave of Conviction",
        "Winter Orb", "Wintertide Brand",
    ],
    "minion": [
        "Absolution", "Animate Guardian", "Animate Weapon", "Blink Arrow",
        "Dominating Blow", "Herald of Agony", "Herald of Purity",
        "Mirror Arrow", "Raise Spectre", "Raise Zombie",
        "Summon Carrion Golem", "Summon Chaos Golem", "Summon Flame Golem",
        "Summon Holy Relic", "Summon Ice Golem", "Summon Lightning Golem",
        "Summon Raging Spirit", "Summon Reaper", "Summon Skeletons",
        "Summon Stone Golem",
    ],
    "totem": [
        "Ancestral Protector", "Ancestral Warchief", "Artillery Ballista",
        "Decoy Totem", "Devouring Totem", "Holy Flame Totem", "Searing Bond",
        "Shockwave Totem", "Shrapnel Ballista", "Siege Ballista",
    ],
    "trap": [
        "Bear Trap", "Blade Trap", "Explosive Trap", "Fire Trap",
        "Flamethrower Trap", "Ice Trap", "Icicle Mine", "Lightning Trap",
        "Lightning Spire Trap", "Seismic Trap", "Siphoning Trap", "Stormblast Mine",
    ],
}

_ALL_SKILLS = [s for skills in SKILLS.values() for s in skills]

_CATEGORY_ALIASES: dict[str, list[str]] = {
    "melee": ["melee", "attack"],
    "range": ["range", "ranged", "archer"],
    "spell": ["spell", "caster"],
    "minion": ["minion", "summoner", "summon"],
    "totem": ["totem", "ballista"],
    "trap": ["trap", "mine"],
}


class PoeBuild(commands.Cog, name="poe"):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _parse_args(args_str: str) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Parse lowercased args string into (use_phrecia, class, ascendancy, skill_category)."""
        use_phrecia = "phrecia" in args_str
        chosen_class = None
        chosen_asc = None

        if use_phrecia:
            for cls, data in CLASSES.items():
                for asc in data["phrecia"]:
                    if asc.lower() in args_str:
                        chosen_class = cls
                        chosen_asc = asc
                        break
                if chosen_asc:
                    break
        else:
            for cls, data in CLASSES.items():
                for asc in data["standard"]:
                    if asc.lower() in args_str:
                        chosen_class = cls
                        chosen_asc = asc
                        break
                if chosen_asc:
                    break
            # Phrecia ascendancy named without the keyword → auto-enable phrecia
            if chosen_asc is None:
                for cls, data in CLASSES.items():
                    for asc in data["phrecia"]:
                        if asc.lower() in args_str:
                            chosen_class = cls
                            chosen_asc = asc
                            use_phrecia = True
                            break
                    if chosen_asc:
                        break

        if chosen_class is None:
            for cls in CLASSES:
                if cls.lower() in args_str:
                    chosen_class = cls
                    break

        chosen_category = None
        for cat, aliases in _CATEGORY_ALIASES.items():
            if any(alias in args_str for alias in aliases):
                chosen_category = cat
                break

        return use_phrecia, chosen_class, chosen_asc, chosen_category

    @commands.command(name="poebuild", aliases=["poe"])
    async def poebuild(self, ctx, *args):
        args_str = " ".join(args).lower()
        use_phrecia, chosen_class, chosen_asc, chosen_category = self._parse_args(args_str)

        if chosen_class is None:
            chosen_class = random.choice(list(CLASSES.keys()))

        league = "phrecia" if use_phrecia else "standard"

        if chosen_asc is None:
            chosen_asc = random.choice(CLASSES[chosen_class][league])

        skill_pool = SKILLS[chosen_category] if chosen_category else _ALL_SKILLS
        chosen_skill = random.choice(skill_pool)

        league_label = "Phrecia" if use_phrecia else "Standard"
        await ctx.send(
            f"**Random PoE Build ({league_label}):**\n"
            f"Class: **{chosen_class}** → **{chosen_asc}**\n"
            f"Skill: **{chosen_skill}**"
        )


async def setup(bot):
    await bot.add_cog(PoeBuild(bot))
