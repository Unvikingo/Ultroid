
from telethon.tl.types import User, Channel
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.errors import RPCError


async def buscar_usuario(event, argumento):
    cliente = event.client

    if not argumento:
        respuesta = await event.get_reply_message()

        if respuesta:
            return await respuesta.get_sender()

        return await cliente.get_me()

    objetivo = argumento.strip()

    if objetivo.lstrip("-").isdigit():
        return await cliente.get_entity(int(objetivo))

    username = objetivo.lstrip("@")

    resultado = await cliente(
        ResolveUsernameRequest(username)
    )

    for usuario in resultado.users:
        if (
            (usuario.username or "").lower()
            == username.lower()
        ):
            return usuario

    return None


async def revisar_grupo(event, usuario):
    chat = await event.get_chat()

    if not isinstance(chat, Channel):
        return (
            "No aplica en este chat",
            "No disponible"
        )

    if not chat.megagroup:
        return (
            "No aplica a canales",
            "No disponible"
        )

    estado = "No se pudo verificar"
    acciones = "No consultadas"

    try:
        permisos = await event.client.get_permissions(
            chat, usuario
        )

        if permisos.is_creator:
            estado = "Propietario"
        elif permisos.is_admin:
            estado = "Administrador"
        elif getattr(permisos, "is_banned", False):
            estado = "Baneado o restringido"
        else:
            estado = "Miembro o sin restricción visible"

    except RPCError:
        pass

    # Solo se consulta el registro si la cuenta
    # tiene permisos de administración.
    try:
        mis_permisos = await event.client.get_permissions(
            chat, "me"
        )

        if not (
            mis_permisos.is_admin
            or mis_permisos.is_creator
        ):
            return estado, "Requiere ser administrador"

        coincidencias = []

        async for accion in event.client.iter_admin_log(
            chat,
            limit=100,
            ban=True,
            unban=True,
            restrict=True,
            unrestrict=True
        ):
            participante = getattr(
                accion.action,
                "participant",
                None
            )

            peer = getattr(
                participante,
                "peer",
                None
            )

            afectado = getattr(
                peer,
                "user_id",
                None
            )

            if afectado is None:
                afectado = getattr(
                    participante,
                    "user_id",
                    None
                )

            if afectado != usuario.id:
                continue

            fecha = accion.date.strftime(
                "%d/%m/%Y %H:%M"
            )

            clase = type(accion.action).__name__

            coincidencias.append(
                f"• {fecha}: {clase}"
            )

            if len(coincidencias) >= 5:
                break

        acciones = (
            "\n".join(coincidencias)
            if coincidencias
            else "Sin coincidencias en los "
                 "últimos 100 eventos consultados"
        )

    except RPCError:
        acciones = "Registro no accesible"

    return estado, acciones


@ultroid_cmd(pattern=r"reportes(?:\s+(.+))?$")
async def reportes(event):
    argumento = event.pattern_match.group(1)

    try:
        usuario = await buscar_usuario(
            event, argumento
        )

        if not isinstance(usuario, User):
            return await event.eor(
                "❌ No se encontró una cuenta "
                "personal o bot accesible."
            )

        nombre = " ".join(
            filter(None, [
                usuario.first_name,
                usuario.last_name
            ])
        ) or "No disponible"

        username = (
            f"@{usuario.username}"
            if usuario.username
            else "No disponible"
        )

        estado, acciones = await revisar_grupo(
            event, usuario
        )

        ficha = (
            "👑 CENTRO DE REPORTES DEL VALHALLA 👑\n\n"
            f"👤 Usuario: {nombre[:80]}\n"
            f"🆔 ID: {usuario.id}\n"
            f"🔗 Username: {username}\n\n"
            "🚨 REPORTES A TELEGRAM\n"
            "• Denunciantes: No disponibles\n"
            "• Cantidad de denuncias: No disponible\n"
            "• Restricciones de cuenta: "
            "Consultar con @SpamBot\n\n"
            "🛡️ MODERACIÓN DEL GRUPO ACTUAL\n"
            f"• Estado: {estado}\n\n"
            "📋 ACCIONES ADMINISTRATIVAS VISIBLES\n"
            f"{acciones}\n\n"
            "🌐 FEDERACIONES\n"
            "• Sin integración autorizada\n"
            "• No existe un registro global universal\n\n"
            "⚔️ ARCHIVOS DEL VALHALLA ⚔️"
        )

        await event.eor(ficha)

    except ValueError:
        await event.eor(
            "❌ No se pudo resolver ese ID o username."
        )

    except RPCError as error:
        await event.eor(
            "❌ Error de Telegram: "
            f"{type(error).__name__}"
        )

    except Exception as error:
        await event.eor(
            f"❌ Error: {type(error).__name__}"
        )
