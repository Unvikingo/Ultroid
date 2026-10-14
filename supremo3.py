"""Investigador Supremo V3: consultas accesibles y moderación de Telegram.
Uso: .supremo3 [@usuario | ID | enlace] o responder a un mensaje.
El decorador ultroid_cmd lo proporciona el cargador de addons de Ultroid.
"""
import io
import os
import json
import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from telethon.errors import RPCError
from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

REDES = {
    'instagram.com': 'Instagram', 'tiktok.com': 'TikTok',
    'facebook.com': 'Facebook', 'youtube.com': 'YouTube',
    'youtu.be': 'YouTube', 'x.com': 'X', 'twitter.com': 'X',
    'twitch.tv': 'Twitch', 'github.com': 'GitHub',
    'linktr.ee': 'Linktree', 'discord.gg': 'Discord',
    'discord.com': 'Discord',
}


def si_no(obj, atributo):
    valor = getattr(obj, atributo, None)
    return 'Sí' if valor is True else ('No' if valor is False else 'No informado')


def limpio(texto, limite=600):
    return str(texto or 'No disponible').replace('\x00', '')[:limite]


def enlaces_publicos(bio):
    encontrados = []
    for url in re.findall(r'https?://[^\s<>\"\']+', bio or '', flags=re.I):
        url = url.rstrip('.,;!?)')
        dominio = (urlparse(url).hostname or '').lower().removeprefix('www.')
        nombre = next((nombre for host, nombre in REDES.items()
                       if dominio == host or dominio.endswith('.' + host)), 'Sitio web')
        item = f'• {nombre}: {url}'
        if item not in encontrados:
            encontrados.append(item)
    return '\n'.join(encontrados[:8]) or 'Sin enlaces publicados en la biografía'


async def resolver(event, argumento):
    if not argumento:
        respuesta = await event.get_reply_message()
        if respuesta:
            usuario = await respuesta.get_sender()
            if usuario:
                return usuario
        return await event.client.get_me()

    texto = argumento.strip().split()[0]
    enlace = re.fullmatch(r'https?://(?:www\.)?t\.me/([A-Za-z][A-Za-z0-9_]{4,31})/?', texto, re.I)
    if enlace:
        texto = enlace.group(1)
    if texto.lstrip('-').isdigit():
        # Los IDs requieren que la entidad ya sea accesible para la sesión.
        return await event.client.get_entity(int(texto))
    nombre = texto.lstrip('@')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{4,31}', nombre):
        raise ValueError('Usuario o ID inválido')
    return await event.client.get_entity('@' + nombre)


async def detalles(event, entidad):
    datos = dict(nombre='No disponible', tipo='Desconocido', bio='Sin información pública', bio_estado='No publicada',
                 comunes='No informado', participantes='No aplica', fecha='No disponible',
                 premium='No informado', extras=[], limitacion='Ninguna')
    if isinstance(entidad, User):
        datos['tipo'] = 'Bot' if entidad.bot else 'Usuario'
        datos['nombre'] = ' '.join(filter(None, [entidad.first_name, entidad.last_name])) or 'Sin nombre visible'
        datos['premium'] = 'No aplica' if entidad.bot else si_no(entidad, 'premium')
        for campo, titulo in [('bot', 'Es bot'), ('deleted', 'Cuenta eliminada'),
                              ('scam', 'Marca scam de Telegram'), ('fake', 'Marca fake de Telegram')]:
            datos['extras'].append(f'{titulo}: {si_no(entidad, campo)}')
        try:
            completo = await event.client(GetFullUserRequest(entidad))
            datos['bio'] = getattr(completo.full_user, 'about', None) or datos['bio']
            if getattr(completo.full_user, 'about', None):
                datos['bio_estado'] = 'Visible'
            comunes = getattr(completo.full_user, 'common_chats_count', None)
            if comunes is not None:
                datos['comunes'] = str(comunes)
        except (RPCError, ValueError) as exc:
            datos['limitacion'] = type(exc).__name__
            datos['bio_estado'] = 'Consulta limitada: ' + type(exc).__name__
    elif isinstance(entidad, (Channel, Chat)):
        datos['tipo'] = ('Supergrupo' if entidad.megagroup else 'Canal') if isinstance(entidad, Channel) else 'Grupo básico'
        datos['nombre'] = entidad.title
        datos['premium'] = 'No aplica'
        fecha = getattr(entidad, 'date', None)
        if fecha:
            datos['fecha'] = fecha.strftime('%d/%m/%Y') + ' (fecha visible del chat)'
        try:
            if isinstance(entidad, Channel):
                completo = await event.client(GetFullChannelRequest(entidad))
            else:
                completo = await event.client(GetFullChatRequest(entidad.id))
            datos['bio'] = getattr(completo.full_chat, 'about', None) or datos['bio']
            if getattr(completo.full_chat, 'about', None):
                datos['bio_estado'] = 'Visible'
            participantes = getattr(completo.full_chat, 'participants_count', None)
            if participantes is not None:
                datos['participantes'] = str(participantes)
        except (RPCError, ValueError) as exc:
            datos['limitacion'] = type(exc).__name__
            datos['bio_estado'] = 'Consulta limitada: ' + type(exc).__name__
    return datos


async def moderacion(event, entidad):
    if not isinstance(entidad, User):
        return 'No aplica', 'No aplica'
    try:
        chat = await event.get_chat()
        if not isinstance(chat, Chat) and not (isinstance(chat, Channel) and chat.megagroup):
            return 'Ejecutado fuera de un grupo', 'No consultable aquí'
        permisos = await event.client.get_permissions(chat, entidad)
        if permisos.is_creator:
            return 'Propietario', 'Sin restricción visible'
        if permisos.is_admin:
            return 'Administrador', 'Sin restricción visible'
        if getattr(permisos, 'is_banned', False):
            return 'Miembro baneado o restringido', 'Restricción visible'
        return 'Miembro / estado accesible', 'Sin restricción visible'
    except (RPCError, ValueError, TypeError):
        return 'No verificable con los permisos actuales', 'No verificable'


async def foto_perfil(event, entidad):
    try:
        return await event.client.download_profile_photo(entidad, file=bytes)
    except (RPCError, ValueError, TypeError):
        return None



def _redis_cliente():
    """Usa Redis de Railway; no guarda datos en disco efímero."""
    import redis
    host = os.getenv('REDISHOST')
    port = int(os.getenv('REDISPORT', '6379'))
    password = os.getenv('REDISPASSWORD') or None
    if not host:
        return None
    return redis.Redis(host=host, port=port, password=password,
                       decode_responses=True, socket_connect_timeout=3,
                       socket_timeout=3)


def _guardar_observacion(entidad):
    """Registra únicamente perfiles consultados explícitamente; máximo 20 cambios."""
    if not isinstance(entidad, User):
        return ['No aplica a grupos o canales'], 'No aplica', 'No aplica'
    nombre = ' '.join(filter(None, [entidad.first_name, entidad.last_name])) or '(sin nombre)'
    alias = ('@' + entidad.username) if entidad.username else '(sin username)'
    actual = {'nombre': nombre[:120], 'username': alias[:80]}
    ahora = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    cliente = _redis_cliente()
    if cliente is None:
        return ['Redis no configurado para el historial'], 'No disponible', 'No disponible'
    clave = f'valhalla:supremo3:historial:{entidad.id}'
    raw = cliente.get(clave)
    try:
        registros = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        registros = []
    if not isinstance(registros, list):
        registros = []
    if not registros or any(registros[-1].get(k) != actual[k] for k in ('nombre', 'username')):
        registros.append({**actual, 'fecha': ahora})
        registros = registros[-20:]
        cliente.set(clave, json.dumps(registros, ensure_ascii=False), ex=90*24*3600)
    else:
        cliente.expire(clave, 90*24*3600)
    lineas = [f"• {r.get('fecha', '?')}: {limpio(r.get('nombre'), 80)} / {limpio(r.get('username'), 60)}"
              for r in registros[-10:]]
    return lineas, registros[0].get('fecha', 'No disponible'), str(max(0, len(registros)-1))


async def historial(entidad):
    try:
        return await asyncio.to_thread(_guardar_observacion, entidad)
    except Exception:
        return ['No disponible (revisar conexión Redis)'], 'No disponible', 'No disponible'


def informe(entidad, datos, rol, restriccion, registros, primera, cambios):
    username = getattr(entidad, 'username', None)
    usuario = '@' + username if username else 'Sin username público'
    enlace = 'https://t.me/' + username if username else 'Sin enlace público'
    ahora = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    tipo = datos['tipo']
    es_usuario = isinstance(entidad, User)
    # No se atribuyen registros locales inexistentes ni se adivinan datos privados.
    lineas = [
        '👑 INVESTIGADOR SUPREMO V3 👑',
        '⚔️ ARCHIVOS DEL VALHALLA ⚔️',
        '', '👤 IDENTIDAD',
        f'Nombre: {limpio(datos["nombre"], 100)}',
        f'ID: {entidad.id}', f'Username: {usuario}',
        f'Tipo: {tipo}', f'Verificado: {si_no(entidad, "verified")}',
        f'Premium: {datos["premium"]}',
        *datos['extras'],
        '', '🛡️ MODERACIÓN Y CHATS',
        f'Rol en el grupo actual: {rol}',
        f'Restricciones en el grupo actual: {restriccion}',
        f'Chats en común (Telegram): {datos["comunes"]}',
        f'Participantes del chat: {datos["participantes"]}',
        'Administración en otros grupos: No consultada',
        'Sanciones de otros grupos: No consultables globalmente',
        '', '📅 INFORMACIÓN ADICIONAL',
        f'Fecha visible: {datos["fecha"]}',
        f'Enlace público: {enlace}',
        f'Consulta: {ahora}',
        '', '📝 BIOGRAFÍA PÚBLICA',
        f'Estado: {datos["bio_estado"]}',
        limpio(datos['bio'], 650),
        '', '🌐 REDES PUBLICADAS EN LA BIO',
        limpio(enlaces_publicos(datos['bio']), 550),
        '', '📚 HISTORIAL Y ACTIVIDAD',
        'Historial de nombres y usernames observados:',
        *registros,
        f'Primera vez observada: {primera}',
        f'Cambios observados: {cambios}',
        'Mensajes contabilizados: Sin registro local',
        'Última actividad: No consultada',
        'Advertencias de moderación: Sin integración con un registro autorizado',
        '', '📍 UBICACIÓN',
        'Ubicación voluntariamente compartida: No consultada',
        'GPS privado e IP: No accesibles',
        '', '🔐 LÍMITES DE PRIVACIDAD',
        'Teléfono oculto: No consultable',
        'Denunciantes: No consultables',
        'Baneos globales: Sin registro universal',
        'Federaciones: Sin integración',
        f'Estado de consulta detallada: {datos["limitacion"]}',
        '', '🐺 EL VALHALLA TODO LO OBSERVA 🐺',
    ]
    return '\n'.join(lineas)


@ultroid_cmd(pattern=r'supremo3(?:\s+(.+))?$')
async def investigador_supremo_v3(event):
    argumento = event.pattern_match.group(1)
    try:
        entidad = await resolver(event, argumento)
        if entidad is None:
            return await event.eor('❌ No se encontró el perfil.')
        datos = await detalles(event, entidad)
        rol, restriccion = await moderacion(event, entidad)
        registros, primera, cambios = await historial(entidad)
        ficha = informe(entidad, datos, rol, restriccion, registros, primera, cambios)
        # Mantener foto de perfil del V2 incluso si el informe es largo.
        # Telegram limita captions; el informe largo se envía aparte.
        foto = await foto_perfil(event, entidad)
        if foto:
            imagen = io.BytesIO(foto)
            imagen.name = 'supremo_v3.jpg'
            try:
                if len(ficha) <= 1000:
                    await event.client.send_file(event.chat_id, imagen, caption=ficha,
                                                 reply_to=event.reply_to_msg_id)
                else:
                    await event.client.send_file(event.chat_id, imagen,
                                                 caption='👑 INVESTIGADOR SUPREMO V3 👑',
                                                 reply_to=event.reply_to_msg_id)
                    await event.client.send_message(event.chat_id, ficha)
                await event.delete()
                return
            except (RPCError, ValueError, TypeError):
                pass
        # Informes muy extensos se entregan como archivo de texto.
        if len(ficha) > 3900:
            archivo = io.BytesIO(ficha.encode('utf-8'))
            archivo.name = 'informe_supremo3.txt'
            await event.client.send_file(event.chat_id, archivo, caption='⚔️ Informe Supremo V3')
            await event.delete()
        else:
            await event.eor(ficha)
    except (RPCError, ValueError) as exc:
        await event.eor('❌ Perfil no accesible o consulta rechazada: ' + type(exc).__name__)
    except Exception as exc:
        await event.eor('❌ Error del addon: ' + type(exc).__name__)
