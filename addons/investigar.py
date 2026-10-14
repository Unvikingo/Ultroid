

from telethon.tl.types import User
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors import RPCError

@ultroid_cmd(pattern=r"investigar(?:\s+(.+))?$")
async def investigar(event):
    objetivo = event.pattern_match.group(1)

    if not objetivo:
        return await event.eor("🔎 Uso: .investigar @usuario")

    try:
        usuario = await event.client.get_entity(objetivo.strip())
return await event.eor(
    f"🔎 Busqué: {objetivo!r}\n"
    f"📌 Encontré: {getattr(usuario, 'username', None)}\n"
    f"📂 Tipo: {type(usuario).__name__}"
)
        # Diagnóstico temporal
        tipo = type(usuario).__name__

        if not isinstance(usuario, User):
            return await event.eor(
                f"🔎 Telegram devolvió: {tipo}"
            )

        nombre = " ".join(
            filter(None, [usuario.first_name, usuario.last_name])
        )

        username = (
            f"@{usuario.username}"
            if usuario.username else "No disponible"
        )

        bio = "No disponible"

        try:
            completo = await event.client(
                GetFullUserRequest(usuario)
            )
            bio = completo.full_user.about or bio
        except RPCError:
            pass

        mensaje = (
            "🔎 PERFIL PÚBLICO DE TELEGRAM\n\n"
            f"👤 Nombre: {nombre}\n"
            f"🆔 ID: {usuario.id}\n"
            f"🔗 Username: {username}\n"
            f"🤖 Bot: {'Sí' if usuario.bot else 'No'}\n"
            f"📝 Bio: {bio}"
        )

        await event.eor(mensaje)

    except (ValueError, RPCError) as error:
        await event.eor(
            f"❌ Error: {type(error).__name__}"
        )

