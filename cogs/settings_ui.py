"""The /castro settings control panel: pick a group, pick a setting, edit it in a form."""

from __future__ import annotations

import discord

from core import config as cfg
from core.schema import BY_KEY, GROUPS, SETTINGS, display_value
from core.ui import embed, ident, reply


def group_settings(group: str):
    return [s for s in SETTINGS if s.group == group]


class EditSettingModal(discord.ui.Modal):
    def __init__(self, view: "SettingsView", setting):
        super().__init__(title=f"Edit: {setting.label}"[:45])
        self.view, self.setting = view, setting
        current = view.bot.settings.get(view.guild_id, setting.key)
        shown = "on" if current is True else "off" if current is False else str(current)
        long_form = setting.kind in ("template", "lines")
        self.box = discord.ui.TextInput(
            label=setting.label[:45],
            default=shown[:4000],
            placeholder=(setting.help or None) and setting.help[:100],
            style=discord.TextStyle.paragraph if long_form else discord.TextStyle.short,
            max_length=min(max(setting.max_len, 60), 4000),
            required=not setting.allow_empty,
        )
        self.add_item(self.box)

    async def on_submit(self, interaction: discord.Interaction):
        ok, message = self.view.bot.settings.set(self.view.guild_id, self.setting.key, self.box.value)
        if not ok:
            return await reply(interaction, embed=embed(f"❌ {self.setting.label}", message, cfg.RED))
        self.view.bot.setting_changed(self.view.guild_id, self.setting.key)
        self.view.rebuild()
        try:
            await interaction.response.edit_message(embed=self.view.render(), view=self.view)
        except discord.HTTPException:
            await reply(interaction, f"✅ Saved **{self.setting.label}**.")


class GroupSelect(discord.ui.Select):
    def __init__(self, view: "SettingsView"):
        options = [discord.SelectOption(label=label, value=key, default=key == view.group) for key, label in GROUPS.items()]
        super().__init__(placeholder="Choose a category…", options=options, row=0)
        self.parent = view

    async def callback(self, interaction: discord.Interaction):
        self.parent.group = self.values[0]
        self.parent.rebuild()
        await interaction.response.edit_message(embed=self.parent.render(), view=self.parent)


class SettingSelect(discord.ui.Select):
    def __init__(self, view: "SettingsView"):
        options = []
        for s in group_settings(view.group):
            custom = not view.bot.settings.values.is_default(view.guild_id, s.key)
            current = display_value(s, view.bot.settings.get(view.guild_id, s.key), 80)
            options.append(discord.SelectOption(label=s.label[:100], value=s.key, description=current[:100],
                                                emoji="✏️" if custom else None))
        super().__init__(placeholder="Pick a setting to change…", options=options, row=1)
        self.parent = view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditSettingModal(self.parent, BY_KEY[self.values[0]]))


class SettingsView(discord.ui.View):
    def __init__(self, bot, owner_id: int, guild_id: int, group: str = "identity"):
        super().__init__(timeout=600)
        self.bot, self.owner_id, self.guild_id, self.group = bot, owner_id, guild_id, group
        self.rebuild()

    def rebuild(self) -> None:
        self.clear_items()
        self.add_item(GroupSelect(self))
        self.add_item(SettingSelect(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await reply(interaction, "This settings panel belongs to someone else. Run `/castro settings` for your own.")
            return False
        return True

    def render(self) -> discord.Embed:
        i = ident(self.guild_id)
        em = embed(f"⚙️ {GROUPS[self.group]}", "Pick a setting in the second menu to edit it. ✏️ marks values you've changed.", i.primary)
        for s in group_settings(self.group):
            value = self.bot.settings.get(self.guild_id, s.key)
            mark = "" if self.bot.settings.values.is_default(self.guild_id, s.key) else " ✏️"
            note = f"\n*{s.help}*" if s.help else ""
            em.add_field(name=f"{s.label}{mark}", value=f"{display_value(s, value)}{note}"[:1024], inline=False)
        em.set_footer(text="Changes apply immediately · /castro reset <setting> restores a default · /castro preview shows messages")
        return em
