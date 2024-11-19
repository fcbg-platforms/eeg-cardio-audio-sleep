from resp_audio_sleep.utils.blocks import _BLOCKS, generate_blocks_sequence


def test_generate_blocks_sequence():
    """Test generation of a random block sequence."""
    blocks = list()
    for _ in range(27):
        blocks.append(generate_blocks_sequence(blocks))
    assert blocks[0] == "baseline"
    assert blocks[1] == "synchronous-respiration"
    assert set(blocks[2:5]) == {"isochronous", "asynchronous", "synchronous-cardiac"}
    assert set(blocks[5:10]) == _BLOCKS
    assert set(blocks[10:15]) == _BLOCKS
    assert set(blocks[15:20]) == _BLOCKS
    assert set(blocks[20:25]) == _BLOCKS
    assert len(set(blocks[25:27])) == 2
