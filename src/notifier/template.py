from datetime import datetime, timezone
from typing import List
from src.scrapers.base import JobPost
from src.profile import profile

PRIMARY = "#0077B5"
ACCENT = "#00A0DC"
SUCCESS = "#057642"
LIGHT_BG = "#F3F6F8"
CARD_BORDER = "#E1E8ED"


def generar_html(jobs: List[JobPost], fecha: str) -> str:
    if not jobs:
        return _html_vacio(fecha)
    cards = ""
    for j in jobs:
        score = j.match_score
        score_color = SUCCESS if score >= 60 else "#E7A33E" if score >= 40 else "#CC4444"
        score_label = f"{int(score)}%"
        posted = ""
        if j.posted_date:
            try:
                posted = j.posted_date.strftime("%d %b %Y")
            except Exception:
                posted = ""
        desc_short = j.description or ""
        if len(desc_short) > 250:
            desc_short = desc_short[:250] + "..."
        cards += f"""
        <tr>
            <td style="padding: 0 0 16px 0;">
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="background: #ffffff; border: 1px solid {CARD_BORDER}; border-radius: 8px; overflow: hidden;">
                    <tr>
                        <td style="padding: 16px 20px;">
                            <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="font-size: 15px; font-weight: 700; color: #1A1A2E; line-height: 1.3;">
                                        <a href="{j.url}" style="color: {PRIMARY}; text-decoration: none;">{j.title}</a>
                                    </td>
                                    <td style="text-align: right; vertical-align: top; white-space: nowrap;">
                                        <span style="background: {score_color}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">{score_label}</span>
                                    </td>
                                </tr>
                            </table>
                            <table width="100%" border="0" cellpadding="0" cellspacing="0" style="margin-top: 6px;">
                                <tr>
                                    <td style="font-size: 13px; color: #555;">{j.company}</td>
                                    <td style="font-size: 12px; color: #888; text-align: right; white-space: nowrap;">{j.source} &bull; {posted}</td>
                                </tr>
                            </table>
                            <table width="100%" border="0" cellpadding="0" cellspacing="0" style="margin-top: 6px;">
                                <tr>
                                    <td style="font-size: 12px; color: #666;">{j.location}</td>
                                    <td style="text-align: right;">
                                        <span style="background: {ACCENT}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 10px;">REMOTE</span>
                                    </td>
                                </tr>
                            </table>
                            <table width="100%" border="0" cellpadding="0" cellspacing="0" style="margin-top: 8px;">
                                <tr>
                                    <td style="font-size: 12px; color: #777; line-height: 1.5;">{desc_short}</td>
                                </tr>
                            </table>
                            <table width="100%" border="0" cellpadding="0" cellspacing="0" style="margin-top: 12px;">
                                <tr>
                                    <td>
                                        <a href="{j.url}" style="display: inline-block; background: {PRIMARY}; color: white; padding: 7px 18px; text-decoration: none; border-radius: 4px; font-size: 12px; font-weight: 600;">Apply Now</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background: {LIGHT_BG};">
    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 680px; margin: 20px auto; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
        <tr>
            <td style="background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%); padding: 24px 20px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 22px; font-weight: 700;">Job Bot Report</h1>
                <p style="color: rgba(255,255,255,0.85); margin: 6px 0 0 0; font-size: 13px;">{profile.name} &bull; {fecha}</p>
            </td>
        </tr>
        <tr>
            <td style="padding: 20px;">
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="background: white; border-radius: 8px; border: 1px solid {CARD_BORDER}; padding: 16px;">
                    <tr>
                        <td style="text-align: center; padding: 10px;">
                            <span style="font-size: 28px; font-weight: 700; color: {PRIMARY};">{len(jobs)}</span>
                            <span style="font-size: 13px; color: #666; display: block;">vacantes nuevas encontradas</span>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td style="padding: 0 20px;">
                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                    {cards}
                </table>
            </td>
        </tr>
        <tr>
            <td style="background: {PRIMARY}; padding: 16px 20px; text-align: center; border-radius: 0 0 12px 12px;">
                <p style="color: white; font-size: 13px; margin: 0;">
                    Bot automatizado &bull; {profile.title} &bull; {profile.location}
                </p>
                <p style="color: rgba(255,255,255,0.7); font-size: 11px; margin: 6px 0 0 0;">
                    Perfil: {len(profile.skills)} skills &bull; English {profile.english_level} &bull; Solo remoto
                </p>
            </td>
        </tr>
    </table>
</body>
</html>"""


def _html_vacio(fecha: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background: {LIGHT_BG};">
    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 680px; margin: 20px auto; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
        <tr>
            <td style="background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%); padding: 24px 20px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 22px;">Job Bot Report</h1>
                <p style="color: rgba(255,255,255,0.85); margin: 6px 0 0 0; font-size: 13px;">{profile.name} &bull; {fecha}</p>
            </td>
        </tr>
        <tr>
            <td style="padding: 40px 20px; text-align: center;">
                <p style="font-size: 16px; color: #666;">No se encontraron vacantes nuevas hoy</p>
                <p style="font-size: 13px; color: #999;">El bot sigue buscando. Te avisamos cuando aparezca algo.</p>
            </td>
        </tr>
    </table>
</body>
</html>"""


def generar_texto(jobs: List[JobPost], fecha: str) -> str:
    if not jobs:
        return f"Job Bot Report - {fecha}\n\nNo se encontraron vacantes nuevas hoy."
    lines = [f"Job Bot Report - {fecha}", f"{len(jobs)} vacantes nuevas encontradas", ""]
    for i, j in enumerate(jobs, 1):
        lines.extend([
            f"{i}. {j.title} ({j.match_score}%)",
            f"   {j.company} | {j.source} | {j.location}",
            f"   {j.url}",
            ""
        ])
    return "\n".join(lines)
