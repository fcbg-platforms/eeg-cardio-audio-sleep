from cardio_audio_sleep.utils.blocks import _BLOCKS, generate_blocks_sequence


def test_generate_blocks_sequence():
    """Test generation of a random block sequence."""
    blocks = list()
    for _ in range(22):
        blocks.append(generate_blocks_sequence(blocks))
    assert blocks[0] == "baseline"
    assert blocks[1] == "synchronous"
    assert set(blocks[2:4]) == {"isochronous", "asynchronous"}
    assert set(blocks[4:8]) == _BLOCKS
    assert set(blocks[8:12]) == _BLOCKS
    assert set(blocks[12:16]) == _BLOCKS
    assert set(blocks[16:20]) == _BLOCKS
    assert len(set(blocks[20:22])) == 2
