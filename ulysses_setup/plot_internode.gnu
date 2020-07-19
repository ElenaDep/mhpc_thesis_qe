set terminal pngcairo enhanced font 'Verdana,10'
set output 'plot_internode.png'
set title "Awsurf benchmark (2 iteration) on ulyssesv2, multiple nodes"
set boxwidth 0.9 relative
set style data histograms
set style fill solid 1.0 border -1
set auto x
set auto y
set key top left
set ylabel "Time(seconds)"
set xlabel "# mpi processes"

plot 'test_rmm_internode' u 3:xticlabels(1) t "rmm", 'test_internode' u 3:xticlabels(1) t "david"

