set terminal pngcairo enhanced font 'Verdana,10'
set output 'plot_david_internode.png'
set title "Awsurf benchmark (2 iteration) on ulyssesv2, multiple nodes"
set boxwidth 0.9 relative
set style data histograms
set style fill solid 1.0 border -1
set auto x
set auto y
set ylabel "WallTime(seconds)"
set xlabel "# mpi processes"

plot 'test_internode' u 3:xticlabels(1) t "inter node" lt rgb '#288D4A'

