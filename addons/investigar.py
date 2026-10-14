


@ultroid_cmd(pattern=r"investigar(?:\s+(.+))?$")
async def investigar(event):
    objetivo = event.pattern_match.group(1)

    if not objetivo:
        return await event.eor(
            "🔎 Uso: .investigar @usuario"
        )

    try:
        objetivo = objetivo.strip()
        usuario = await event.client.get_entity(objetivo)

        resultado = (
            "🔎 DIAGNÓSTICO\n\n"
            f"🔍 Busqué: {objetivo}\n"
            f"👤 Encontré: {getattr(usuario, 'username', None)}\n"
            f"📂 Tipo: {type(usuario).__name__}"
        )

        await event.eor(resultado)

    except Exception as error:
        await event.eor(
            f"❌ Error: {type(error).__name__}"
        )


