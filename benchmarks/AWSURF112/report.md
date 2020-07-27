## Quantum Espresso: Ausurf benchmark of RMM-DIIS alorithm and Davidson algorithm

### Installation

I installed the version of 6.5.1 release of QE, in the parallel set-up linking the extarnal lapack and scalapack libraries.

```
./configure --enable-openmp --with-sclapack=intel
```

And i compile with intel compiler. loading the following modules:

```
 1) intel/pe-xe-2018--binary                
 2) intelmpi/2018--binary                   
 3) mkl/2018--binary                        
 4) scalapack/2.0.2--intelmpi--2018--binary 
```

### MPI scaling , 10 iterations

In this section a report  the analysis on the MPI-scaling of the two algorithms when i increased the number of nodes and of processors (36*n_node ).

To run the simulation i exported the OMP_NUM_THREADS to 1 and repeated it on 1, 2, 4, 8, 16 nodes.

 I used the input file of the ausurf benchmark where i change the `electron_maxstep=10`, to make it a bit longer so that i could make it run consistently even for a large number of nodes.

In this analysis i don't want to compare the two algorithms between them as the kind of steps that they're are doing are different and it doesn't make sense to compare them not in a full convergence test. I will present a comparison between them in the following section, together with some report of profiling tools for intel. 

In the section i report how they scale increasing the number of MPI processes, using the python script to produce the output `graph.py`. In the script, there is a variable called **at_least** which define a threshold value in percent. If the code spent, in a subroutine, more than at_leastpercent of time of the caller routine then the subroutine will be
displayed on the graph. By default this value is set to **10%**.

#### Davidson Algorithm

![](galileo/ausurf_internode_10it/MPI_scaling_ausurf-output_davidson.png)

#### RMM-DIIS Algorithm

 

![](galileo/ausurf_internode_10it/MPI_scaling_ausurf-output_rmm-diis.png)

### Convergence test

 I used the input file of the ausurf benchmark where i change the `electron_maxstep=1000`,  to be sure to not limited the number of steps before the algorithm stop as they arrive at the convergence. 

I run the simulations with : 

- 1 node , 36 processes, 1 OMP thread 

| ALGORITHM | CPU_TIME  | WALL_TIME | Total energy       | #of iterations |
| --------- | --------- | --------- | ------------------ | -------------- |
| DAVIDSON  | 15m15.04s | 16m37.67s | -11427.09402151 Ry | 22             |
| RMM-DIIS  | 12m49.36s | 13m51.65s | -11427.09402088 Ry | 22             |



- 2 nodes,  72 processes, 1 OMP thread

| ALGORITHM | CPU_TIME | WALL_TIME | Total energy    | #of iterations |
| --------- | -------- | --------- | --------------- | -------------- |
| DAVIDSON  | 9m 7.05s | 11m 8.92s | -11427.09402124 | 21             |
| RMM-DIIS  | 8m 1.42s | 9m 0.01s  | -11427.09402106 | 22             |



- 4 nodes,  144 processes, 1 OMP thread

| ALGORITHM | CPU_TIME | WALL_TIME | Total energy    | #of iterations |
| --------- | -------- | --------- | --------------- | -------------- |
| DAVIDSON  | 7m43.79s | 8m50.93s  | -11427.09402100 | 21             |
| RMM-DIIS  | 9m 1.55s | 9m59.13s  | -11427.09402140 | 22             |



- 8 nodes,  288 processes, 1 OMP thread

| ALGORITHM | CPU_TIME | WALL_TIME | Total energy    | #of iterations |
| --------- | -------- | --------- | --------------- | -------------- |
| DAVIDSON  | 6m 5.09s | 7m15.96s  | -11427.09402122 | 21             |
| RMM-DIIS  | 3m38.36s | 4m38.81s  | -11427.09402120 | 23             |



- 16 nodes,  576 processes, 1 OMP thread

| ALGORITHM | CPU_TIME | WALL_TIME | Total energy    | #of iterations |
| --------- | -------- | --------- | --------------- | -------------- |
| DAVIDSON  | 5m33.78s | 6m43.58s  | -11427.09402111 | 21             |
| RMM-DIIS  | 5m 8.57s | 6m10.67s  | -11427.09402151 | 24             |

### APS report

I repeat the run on 1 node using the profiling tool of APS (Application Performance Snapshot), these are the report that i obtained.

##### Davidson

##### <img src="galileo/aps/aps-report_ausurf-output_dav_1nd_convergence.png" alt="aps-report_ausurf-output_rmm_1nd_convergence" style="zoom:200%;" />





##### RMM-DIIS

![aps-report_ausurf-output_dav_1nd_convergence](galileo/aps/aps-report_ausurf-output_rmm_1nd_convergence.png)



