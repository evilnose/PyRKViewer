import pstats
from pstats import SortKey

p = pstats.Stats('rkviewer.stat')

p.sort_stats(SortKey.CUMULATIVE).print_stats(20)
