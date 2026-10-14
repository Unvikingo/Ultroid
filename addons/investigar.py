
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors import RPCError

@ultroid_cmd(pattern=r"investigar(?:\s+(.+))?$")
async def investigar(event):
    objetivo = event.pattern_match.group(1)

    if not objetivo:
        return await event.eor(
            "🔎 Uso: .investigar @usuario"
        )

    try:
        usuario = await event.client.get_entity(
            objetivo.strip()
        )

        if not hasattr(usuario, "first_name"):
            return await event.eor(
                "No se encontró una cuenta de usuario."
            )

        nombre = " ".join(
            filter(None, [
                usuario.first_name,
                usuario.last_name
            ])
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

    except (ValueError, RPCError):
        await event.eor(
            "❌ No se pudo consultar ese perfil."
        )
