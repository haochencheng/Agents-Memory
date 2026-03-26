from __future__ import annotations

from agents_memory.services.vector import cmd_embed, cmd_to_qdrant, cmd_vsearch


def register() -> dict[str, callable]:
    def handle_vsearch(ctx, args):
        if not args:
            print("用法: python3 memory.py vsearch <query>")
            return
        top_k = int(args[-1]) if args[-1].isdigit() else 5
        query = " ".join(args[:-1] if args[-1].isdigit() else args)
        cmd_vsearch(ctx, query, top_k)

    return {
        "embed": lambda ctx, args: cmd_embed(ctx),
        "vsearch": handle_vsearch,
        "to-qdrant": lambda ctx, args: cmd_to_qdrant(ctx),
    }
