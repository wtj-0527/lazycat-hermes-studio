from pathlib import Path


MANIFEST = Path(__file__).resolve().parents[1] / "lzc-manifest.yml"


def test_rootfs_snapshot_uses_watchcat_fifo_and_idle_io():
    manifest = MANIFEST.read_text()
    assert "/api/v1/upgrade-coordinator" in manifest
    assert "acquire_upgrade_slot" in manifest
    assert "release_upgrade_slot" in manifest
    assert "ionice -c 3 nice -n 15" in manifest
    assert 'run_idle rm -rf "$BASE/$d"' in manifest
    assert 'run_idle cp -a "/$d/." "$BASE/$d/"' in manifest


def test_rootfs_snapshot_does_not_rescan_destination_for_progress():
    manifest = MANIFEST.read_text()
    snapshot = manifest.split('if [ "$NEED_SNAPSHOT" = "1" ]; then', 1)[1].split(
        "# --- Sync container-generated files", 1
    )[0]
    assert "du -sh" not in snapshot
