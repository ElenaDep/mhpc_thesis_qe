set terminal pngcairo enhanced font 'Verdana,10'
set output 'plot_intranode.png'
set title "Awsurf benchmark (1 iteration) on ulyssesv2"
set boxwidth 0.9 relative
set style data histograms
set style fill solid 1.0 border -1
set auto x
set auto y
set ylabel "Time(seconds)"
set xlabel "# mpi processes"

plot 'test_it1_david.dat' u 3:xticlabels(1) t "intranode"

