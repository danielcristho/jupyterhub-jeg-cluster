"""Handle pre-spawn and post-start"""
from spawner.multinode import PatchedMultiNodeSpawner

def attach_hooks():
    PatchedMultiNodeSpawner.pre_spawn_hook = staticmethod(
        lambda spawner: spawner.log.info(f"[HOOK] pre_spawn {spawner.user.name}")
    )
    PatchedMultiNodeSpawner.post_start_hook = staticmethod(
        lambda spawner: spawner.log.info(f"[HOOK] post_start {spawner.user.name}")
    )
