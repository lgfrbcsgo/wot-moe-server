from debug_utils import LOG_CURRENT_EXCEPTION


def init():
    try:
        from mod_moe_server.server import g_moe_server

        g_moe_server.serve()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def fini():
    try:
        from mod_moe_server.server import g_moe_server

        g_moe_server.close()
    except Exception:
        LOG_CURRENT_EXCEPTION()
