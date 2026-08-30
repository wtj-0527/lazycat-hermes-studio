from pathlib import Path


MANIFEST = Path(__file__).resolve().parents[1] / "lzc-manifest.yml"


def test_rootfs_snapshot_uses_watchcat_fifo_and_idle_io():
    manifest = MANIFEST.read_text()
    assert "hermes-studio-rootfs-upgrade-lock" in manifest
    assert "community.lazycat.app.hermes.upgrade.queue" in manifest
    assert "docker run -d --rm --name" in manifest
    assert "FIRST_WAITING" in manifest
    assert 'LOCK_IMAGE=$CURRENT_IMAGE' in manifest
    assert 'docker image inspect "$LOCK_IMAGE"' in manifest
    assert "UPGRADE_PROGRESS_LABEL" in manifest
    assert "cleanup_stale_upgrade_markers" in manifest
    assert "UPGRADE_HEARTBEAT_PID" in manifest
    assert "acquire_upgrade_slot" in manifest
    assert "release_upgrade_slot" in manifest
    assert "ionice -c 3 nice -n 15" in manifest
    assert 'run_idle rm -rf "$BASE/$d"' in manifest
    assert 'cp -a "/$d/." "$BASE/$d/" &' in manifest


def test_rootfs_snapshot_does_not_rescan_destination_for_progress():
    manifest = MANIFEST.read_text()
    snapshot = manifest.split('if [ "$NEED_SNAPSHOT" = "1" ]; then', 1)[1].split(
        "# --- Sync container-generated files", 1
    )[0]
    assert 'du -s' not in snapshot.replace('du -sb "/$d"', "")
    assert 'du -sb "$BASE' not in snapshot
    assert '"/proc/$COPY_PID/io"' in snapshot
    assert 'write_progress "copy-$d"' in snapshot
    assert "PERCENT" in snapshot


def test_manifest_only_updates_do_not_rebuild_the_rootfs_base():
    manifest = MANIFEST.read_text()
    assert 'CURRENT_IMAGE=$(awk' in manifest
    assert '"$ROOTFS/.image-ref"' in manifest
    assert "migrated rootfs image fingerprint without re-snapshotting" not in manifest
    assert 'elif [ "$CURRENT_IMAGE" != "$STORED_IMAGE" ]; then' in manifest
