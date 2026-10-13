


VIKING_IMAGE = (
    "https://raw.githubusercontent.com/Unvikingo/Ultroid/"
    "main/AC11F862-18E3-42E1-B890-17B88A8C6D3B.png"
)

VIKING_TEXT = """
⚔️ EL VIKINGO HA LLEGADO ⚔️

🐺 El Valhalla tiene dueño.
👑 Mi presencia no se anuncia, se siente.
🔥 No vine a pedir permiso. Vine a imponer presencia.

⚡ EL REY DEL VALHALLA ⚡
"""


@ultroid_cmd(pattern="valhalla$")
async def valhalla(event):
    try:
        await event.client.send_file(
            event.chat_id,
            VIKING_IMAGE,
            caption=VIKING_TEXT,
            reply_to=event.id,
        )
        await event.delete()
    except Exception:
        await event.eor("Error al enviar la imagen.")

@ultroid_cmd(pattern="rey$")
async def rey(event):
    try:
        await event.client.send_file(
            event.chat_id,
            VIKING_IMAGE,
            caption=(
                "👑 EL REY HA LLEGADO 👑\n\n"
                "⚔️ El trono tiene dueño.\n"
                "🐺 Los lobos conocen a su rey.\n"
                "🔥 El Valhalla reconoce mi presencia.\n\n"
                "⚡ EL VIKINGO ⚡"
            ),
            reply_to=event.id,
        )
        await event.delete()
    except Exception:
        await event.eor("Error al enviar la imagen del rey.")
