# VALHALLA V1.3 — CONSULTA DE VOZ (SOLO LECTURA)
# Complemento de Ultroid: comando .vclista
# No registra comandos de moderacion ni modifica llamadas.

from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.phone import GetGroupParticipantsRequest
from telethon import utils


@ultroid_cmd(
    pattern=r"vclista$",
    owner_only=True,
    groups_only=True,
    admins_only=True,
)
async def vclista(event):
    try:
        chat = await event.get_chat()
        if not getattr(chat, "megagroup", False):
            return await event.eor("⚠️ Usa .vclista en un supergrupo.")

        full = await event.client(GetFullChannelRequest(chat))
        call = getattr(full.full_chat, "call", None)
        if call is None:
            return await event.eor("🐺 No hay chat de voz activo.")

        people = []
        user_map = {}
        chat_map = {}
        offset = ""
        seen = set()

        # El resultado incluye los perfiles accesibles a esta cuenta.
        # No es necesario conectarse como participante de la llamada.
        for _ in range(30):
            result = await event.client(
                GetGroupParticipantsRequest(
                    call=call, ids=[], sources=[], offset=offset, limit=100
                )
            )
            people.extend(result.participants)
            user_map.update({user.id: user for user in result.users})
            chat_map.update({channel.id: channel for channel in result.chats})
            next_offset = getattr(result, "next_offset", "")
            if not next_offset or next_offset == offset or next_offset in seen:
                break
            seen.add(offset)
            offset = next_offset

        lines = [
            "👑 CONTROL SUPREMO DE VOZ 👑",
            "⚔️ PARTICIPANTES DEL VALHALLA ⚔️",
            "",
            f"🐺 Conectados encontrados: {len(people)}",
            "",
        ]
        if not people:
            lines.append("No se encontraron participantes.")

        for number, participant in enumerate(people, 1):
            peer = participant.peer
            if hasattr(peer, "user_id"):
                entity_id = peer.user_id
                entity = user_map.get(entity_id)
                name = utils.get_display_name(entity) if entity else "Usuario sin nombre disponible"
            elif hasattr(peer, "channel_id"):
                entity_id = peer.channel_id
                entity = chat_map.get(entity_id)
                name = getattr(entity, "title", None) or "Canal sin nombre disponible"
            else:
                entity_id = "No disponible"
                entity = None
                name = "Participante"

            username = getattr(entity, "username", None)
            user_label = f"@{username}" if username else "Sin @usuario público"
            # Evitar saltos de línea que puedan desordenar el reporte.
            name = " ".join((name or "Sin nombre disponible").split())
            line = f"{number}. 👤 {name} — {user_label} — ID: {entity_id}"
            if len("\n".join(lines)) + len(line) + 1 > 3800:
                lines.append("⚠️ Lista recortada por límite de Telegram.")
                break
            lines.append(line)

        await event.eor("\n".join(lines))
    except Exception as exc:
        await event.eor(
            f"⚠️ No se pudo consultar la llamada: {type(exc).__name__}: {exc}"
        )
