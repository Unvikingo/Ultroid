
import re
from datetime import timezone

from telethon.tl.types import (
    User, Channel, Chat,
    PeerUser, PeerChannel, PeerChat
)
from telethon.tl.functions.contacts import (
    ResolveUsernameRequest
)
from telethon.tl.functions.users import (
    GetFullUserRequest
)
from telethon.tl.functions.channels import (
    GetFullChannelRequest
)
from telethon.tl.functions.messages import (
    GetFullChatRequest
)
from telethon.errors import RPCError


def nombre_de(entidad):
    if isinstance(entidad, User):
        return " ".join(filter(None, [
            entidad.first_name,
            entidad.last_name
        ])) or "Sin nombre público"

    return getattr(
        entidad, "title", "Sin nombre público"
    )


def tipo_de(entidad):
    if isinstance(entidad, User):
        return "Bot" if entidad.bot else "Usuario"

    if isinstance(entidad, Channel):
        if entidad.megagroup:
            return "Supergrupo"
        return "Canal"

    if isinstance(entidad, Chat):
        return "Grupo básico"

    return "Entidad desconocida"


def usuario_de(entidad):
    username = getattr(entidad, "username", None)
    return f"@{username}" if username else "Sin username"


def fecha_de(fecha):
    if not fecha:
        return "Sin fecha"

    return fecha.strftime("%d/%m/%Y %H:%M UTC")


async def resolver(event, texto=None):
    cliente = event.client

    if not texto:
        respuesta = await event.get_reply_message()

        if respuesta:
            if isinstance(
                respuesta.peer_id,
                (PeerChannel, PeerChat)
            ) and isinstance(
                respuesta.from_id,
                (PeerChannel, PeerChat)
            ):
                return await respuesta.get_sender()

            remitente = await respuesta.get_sender()

            if remitente:
                return remitente

        return await cliente.get_me()

    texto = texto.strip()

    enlace = re.match(
        r"^https?://(?:www\.)?t\.me/([^/?#]+)",
        texto,
        re.IGNORECASE
    )

    if enlace:
        texto = enlace.group(1)

    if texto.lstrip("-").isdigit():
        return await cliente.get_entity(int(texto))

    username = texto.lstrip("@")

    if not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_]{4,31}",
        username
    ):
        raise ValueError("Formato inválido")

    resultado = await cliente(
        ResolveUsernameRequest(username)
    )

    entidades = (
        list(resultado.users)
        + list(resultado.chats)
    )

    for entidad in entidades:
        actual = (
            getattr(entidad, "username", None)
            or ""
        )

        if actual.lower() == username.lower():
            return entidad

    raise ValueError("Entidad no encontrada")


async def detalles(event, entidad):
    info = {
        "bio": "No publicada o no accesible",
        "comunes": "No informado",
        "miembros": "No informado",
        "fecha": "No informada",
        "consulta": "Completada"
    }

    try:
        if isinstance(entidad, User):
            completo = await event.client(
                GetFullUserRequest(entidad)
            )

            info["bio"] = (
                completo.full_user.about
                or "Sin biografía publicada"
            )

            comunes = getattr(
                completo.full_user,
                "common_chats_count",
                None
            )

            if comunes is not None:
                info["comunes"] = str(comunes)

            info["miembros"] = "No aplica"

        elif isinstance(entidad, Channel):
            completo = await event.client(
                GetFullChannelRequest(entidad)
            )

            info["bio"] = (
                completo.full_chat.about
                or "Sin descripción publicada"
            )

            cantidad = getattr(
                completo.full_chat,
                "participants_count",
                None
            )

            if cantidad is not None:
                info["miembros"] = str(cantidad)

            fecha = getattr(entidad, "date", None)

            if fecha:
                info["fecha"] = (
                    fecha_de(fecha)
                    + " (fecha visible de Telegram)"
                )

        elif isinstance(entidad, Chat):
            completo = await event.client(
                GetFullChatRequest(entidad.id)
            )

            info["bio"] = (
                getattr(
                    completo.full_chat,
                    "about",
                    None
                )
                or "Sin descripción publicada"
            )

            cantidad = getattr(
                completo.full_chat,
                "participants_count",
                None
            )

            if cantidad is not None:
                info["miembros"] = str(cantidad)

    except RPCError as error:
        info["consulta"] = (
            "Limitada: " + type(error).__name__
        )

    return info


async def revisar_moderacion(
    event, objetivo, grupo
):
    resultado = {
        "grupo": "No seleccionado",
        "estado": "No aplica",
        "registro": "No consultado",
        "permisos": "No comprobados"
    }

    if grupo is None:
        resultado["estado"] = (
            "Indica un grupo para consultar moderación"
        )
        return resultado

    resultado["grupo"] = (
        nombre_de(grupo)
        + " (ID: "
        + str(grupo.id)
        + ")"
    )

    if not isinstance(objetivo, User):
        resultado["estado"] = (
            "Las sanciones individuales "
            "requieren seleccionar un usuario"
        )
        return resultado

    if isinstance(grupo, Chat):
        resultado["estado"] = (
            "Grupo básico: consulta limitada"
        )
        resultado["registro"] = (
            "El historial administrativo de "
            "supergrupos no aplica aquí"
        )
        return resultado

    if not isinstance(grupo, Channel):
        resultado["estado"] = (
            "El destino no es un grupo"
        )
        return resultado

    if not grupo.megagroup:
        resultado["estado"] = (
            "El destino es un canal, "
            "no un supergrupo"
        )
        return resultado

    try:
        permisos = await event.client.get_permissions(
            grupo,
            objetivo
        )

        if permisos.is_creator:
            resultado["estado"] = "Propietario"

        elif permisos.is_admin:
            resultado["estado"] = "Administrador"

        elif getattr(permisos, "is_banned", False):
            resultado["estado"] = (
                "Baneado o restringido"
            )

        else:
            resultado["estado"] = (
                "Sin restricción visible"
            )

    except (RPCError, ValueError, TypeError):
        resultado["estado"] = (
            "No verificable; puede estar "
            "fuera del grupo"
        )

    try:
        propios = await event.client.get_permissions(
            grupo,
            "me"
        )

        autorizado = (
            propios.is_admin
            or propios.is_creator
        )

        resultado["permisos"] = (
            "Administrador"
            if autorizado
            else "Sin permisos administrativos"
        )

        if not autorizado:
            resultado["registro"] = (
                "Requiere ser administrador"
            )
            return resultado

    except (RPCError, ValueError, TypeError):
        resultado["registro"] = (
            "No se pudieron comprobar permisos"
        )
        return resultado

    encontrados = []
    examinados = 0

    try:
        async for accion in event.client.iter_admin_log(
            grupo,
            limit=100,
            ban=True,
            unban=True,
            restrict=True,
            unrestrict=True
        ):
            examinados += 1

            evento = accion.original
            objeto = evento.action

            participante = getattr(
                objeto,
                "participant",
                None
            )

            afectado = getattr(
                participante,
                "user_id",
                None
            )

            if afectado is None:
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

            # Algunas acciones contienen
            # el usuario afectado en otra
            # estructura del evento.
            if afectado is None:
                afectado = getattr(
                    objeto,
                    "user_id",
                    None
                )

            if afectado != objetivo.id:
                continue

            responsable = getattr(
                evento,
                "user_id",
                None
            )

            accion_tipo = type(objeto).__name__

            if "Banned" in accion_tipo:
                etiqueta = "Cambio de restricción"
            elif "Admin" in accion_tipo:
                etiqueta = "Cambio administrativo"
            else:
                etiqueta = "Acción administrativa"

            encontrados.append(
                f"• {fecha_de(evento.date)}\n"
                f"  {etiqueta}\n"
                f"  Responsable ID: "
                f"{responsable or 'No informado'}"
            )

            if len(encontrados) >= 5:
                break

        if encontrados:
            resultado["registro"] = (
                "\n".join(encontrados)
            )
        else:
            resultado["registro"] = (
                "Sin sanciones coincidentes "
                f"entre {examinados} eventos "
                "administrativos revisados. "
                "No demuestra ausencia de reportes."
            )

    except (RPCError, ValueError, TypeError):
        resultado["registro"] = (
            "Registro no accesible o "
            "sin permisos suficientes"
        )

    return resultado


@ultroid_cmd(
    pattern=r"reportes2(?:\s+(.+))?$"
)
async def centro_reportes_v2(event):
    entrada = event.pattern_match.group(1)

    try:
        partes = entrada.split() if entrada else []

        if len(partes) > 2:
            return await event.eor(
                "❌ Demasiados argumentos.\n\n"
                "Usos:\n"
                ".reportes2\n"
                ".reportes2 @usuario\n"
                ".reportes2 123456789\n"
                ".reportes2 @usuario @grupo\n"
                ".reportes2 @grupo\n"
                "O responde a un mensaje."
            )

        objetivo = None
        grupo = None

        if len(partes) == 2:
            objetivo = await resolver(
                event, partes[0]
            )

            grupo = await resolver(
                event, partes[1]
            )

        elif len(partes) == 1:
            objetivo = await resolver(
                event, partes[0]
            )

        else:
            objetivo = await resolver(event)

        if not isinstance(
            objetivo, (User, Channel, Chat)
        ):
            return await event.eor(
                "❌ Entidad no compatible."
            )

        # Si el objetivo es un grupo,
        # mostramos sus datos públicos.
        # Si es un usuario, podemos
        # revisar su moderación.

        if isinstance(objetivo, User):
            if grupo is None:
                chat = await event.get_chat()

                if isinstance(chat, (Channel, Chat)):
                    grupo = chat

        if grupo is not None:
            if not isinstance(grupo, (Channel, Chat)):
                return await event.eor(
                    "❌ El segundo argumento "
                    "debe ser un grupo accesible."
                )

        info = await detalles(
            event, objetivo
        )

        moderacion = await revisar_moderacion(
            event, objetivo, grupo
        )

        verificado = (
            "Sí"
            if getattr(objetivo, "verified", False)
            else "No"
        )

        ficha = (
            "👑 CENTRO DE REPORTES V2 👑\n"
            "⚔️ ARCHIVOS DEL VALHALLA ⚔️\n\n"

            "🔎 OBJETIVO\n"
            f"Nombre: {nombre_de(objetivo)[:100]}\n"
            f"ID: {objetivo.id}\n"
            f"Username: {usuario_de(objetivo)}\n"
            f"Tipo: {tipo_de(objetivo)}\n"
            f"Verificado: {verificado}\n\n"

            "📊 INFORMACIÓN ACCESIBLE\n"
            f"Chats comunes: {info['comunes']}\n"
            f"Participantes: {info['miembros']}\n"
            f"Fecha visible: {info['fecha']}\n"
            f"Consulta: {info['consulta']}\n\n"

            "📝 BIO / DESCRIPCIÓN\n"
            f"{info['bio'][:350]}\n\n"

            "🚨 REPORTES A TELEGRAM\n"
            "Denunciantes: Confidenciales\n"
            "Cantidad: No proporcionada por Telegram\n"
            "Restricciones personales: "
            "Consultar @SpamBot desde "
            "la propia cuenta\n\n"

            "🛡️ MODERACIÓN DEL GRUPO\n"
            f"Grupo: {moderacion['grupo']}\n"
            f"Estado: {moderacion['estado']}\n"
            f"Permisos: {moderacion['permisos']}\n\n"

            "📋 HISTORIAL ADMINISTRATIVO\n"
            f"{moderacion['registro']}\n\n"

            "🌐 FEDERACIONES\n"
            "Sin integración autorizada\n"
            "No existe una lista universal "
            "de baneos\n\n"

            "🐺 EL VALHALLA TODO LO OBSERVA 🐺"
        )

        # Telegram permite mensajes de
        # texto de hasta 4096 caracteres.
        await event.eor(ficha[:4000])

    except ValueError:
        await event.eor(
            "❌ ID, username o grupo inválido "
            "o no accesible para tu sesión."
        )

    except RPCError as error:
        await event.eor(
            "❌ Error de Telegram: "
            + type(error).__name__
        )

    except Exception as error:
        await event.eor(
            "❌ Error del addon: "
            + type(error).__name__
        )
