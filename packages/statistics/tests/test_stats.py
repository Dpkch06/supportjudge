from supportjudge_statistics.stats import interval, percentile


def test_bootstrap_is_reproducible_and_handles_empty():
    assert interval([]) is None
    assert interval([2,2,2]) == [2,2]
    assert interval([0,1,4]) == interval([0,1,4])


def test_latency_percentile_interpolation():
    assert percentile([1,3],.5) == 2
    assert percentile([],.99) is None
