import sys, os.path
import matplotlib.pyplot as plt
import numpy as np

# list of matplotlib colors
lcolors = ["lightcoral", "lightsalmon", "palegoldenrod"]
lcolors += ["palegreen", "yellowgreen", "skyblue", "paleturquoise"]
lcolors += ["plum", "lavender", "violet", "pink", "magenta", "purple"]

# find type of run: MPI, MPI+OPENMP, MPI+GPU, MPI+OPENMP+GPU
#                   number of threads &| process
def run_info(filename):

  # open file
  nlines_to_read = 120
  with open(filename) as fn: 
    
    # information should be in the first nlines_to_read lines
    file_data = [next(fn) for x in range(nlines_to_read)]
   
    # initialize info 
    nprocess = 0
    nnodes = 0
    nthreads = 0
    mpi_found = False
    node_found = False
    openmp_found = False
    gpu_found = False
    parallelism = ""

    # 13, 14, 53 general position of info about MPI, OPENMP, CUDA
    # but it could probably change
    for i in range(0, nlines_to_read):
      if( "Number of MPI process" in file_data[i] and not mpi_found):
        nprocess = int(file_data[i].replace(" ","").split(":")[1])
        mpi_found = True
     
      if( "MPI processes distributed" in file_data[i] and not node_found ):
        nnodes = int(file_data[i].split("on")[1].replace(" ","").split("nodes")[0])
        node_found = True

      if( "Threads/MPI process" in file_data[i] and not openmp_found ):
        nthreads = int(file_data[i].replace(" ","").split(":")[1])
        openmp_found = True

      # fix for serial version
      if( "Serial multi-threaded" in file_data[i] and not openmp_found ):
        tmp = file_data[i].split("running on")[1].split("processor")[0]
        nthreads = int(tmp.replace(" ",""))
        # print("\n>>>>> ", tmp)
        openmp_found = True
  
      # no info yet about the number of GPU
      if( "GPU acceleration " in file_data[i] and "ACTIVE" in file_data[i]):
        gpu_found = True

      if( openmp_found and mpi_found and gpu_found ):
        break
    
    process_threads_info = ""
    if( node_found and nnodes > 1 ):
        parallelism += "Node "
        process_threads_info +=  str(nnodes)

    # if( mpi_found and nprocess > 1):
    if( mpi_found ):
      parallelism += "MPI"
      
      if( nnodes > 1 ):
        nprocess = int(nprocess / nnodes)
        process_threads_info += " - "
      
      process_threads_info += str(nprocess)
  
    # if( openmp_found and nthreads > 1 ):
    if( openmp_found ):
      parallelism += " OMP"
      if( mpi_found ):
        process_threads_info += " - "
      process_threads_info += str(nthreads) #+ " threads/MPI "
    
    if( gpu_found ):
        parallelism += " GPU "
        print("\t> assuming 1GPU / node !")
        process_threads_info += " - " + str(1) #+ " GPU/Node "

    if( process_threads_info != "" ):
      parallelism +=  " (" + process_threads_info + ")"

  return (nprocess, nthreads, parallelism)

## parse timing information of type "time_ref" from "filename"
## time_ref should be in genral "WALL" and not "CPU"
##
def run_timing(filename, time_ref):

  # open file
  with open(filename) as fn: 
    
    # find where timing starts in the output file
    for line in fn:
      if( not line ):
        break
      else:
        if( "Writing output data file" in line ):
          break
    
    # stars parsing timing data
    timing = {}
    for line in fn:
      if( not line ):
          break
      else:
        line = line.replace('\n','')
        if( time_ref in line ):
          tmp = list(filter(None, line.split(" ")))
          for i in range(0, len(tmp)):
            if( tmp[i] == time_ref):
              if('m' in tmp[i-1] ):
                tmp_2 = tmp[i-1].split('m')
                time_i = 60.0*(float(tmp_2[0]))
                time_i += float(tmp_2[1].replace('s',''))
              else:
                time_i = float(tmp[i-1].replace('s',''))

              break
          timing[tmp[0]] = time_i
          print("\n\t> Time for : "+tmp[0]+" = "+str(time_i))

    return timing

## parse timing information of type "time_ref" from "filename"
## time_ref should be in genral "WALL" and not "CPU" and root
## is the name of the root routine or label for total time
## for Q-E PW it is PWSCF
## 
## Improved version of function 'run_timing' which take care
## of which routine is called inside which other.
##
## Return value are : main_routines, called_routines, hierarchy, total_time
##                    main_routines: dict, keys = routine name, values= [time, to_be_skip]
##                    called_routines: dict, keys = routine name, values= [time, to_be_skip]
##                    hierarchy: dict, keyrs = routine name, values= list of called routine
##                    total_time: total time of run according to time_ref and root
##                                where keyword "PWSCF" in PW package of Q-E
##
def run_timing_improved(filename, time_ref, root, threshold):

  # dict of main routine with times
  main_routines = {}

  # dict of hierarchy, for example : "electron":["c_bands","sum_band","v_fo_rho"]
  hierarchy = {}

  # dict of called routine with their respective timing, ex: "c_bands":806.0
  called_routines = {}

  # total walltime which is given by root id
  # nroot_found this should be equal to one,
  # meaning that 'root' was found only once
  nroot_found = 0
  total_walltime = 0.0

  # open file
  with open(filename) as fn: 
    
    # find where timing starts in the output file
    line_num_start_time=0
    for line in fn:
      # end of file
      if( not line ):
        break
      else:
        if( "Writing output data file" in line ):
          break
        else:
          line_num_start_time += 1

    # get main routine which are the routine name after "writing output data .."
    # until first "called by " expression
    #
    # TODO: Adjust skip value according to 10% of walltime
    info_started = False
    for line in fn:
      line = line.replace("\n","")

      # skip empty line
      if( line.replace(" ","") !=  ""  ):

        # we arrive to description of hierarchy of calls
        # this should no happen
        if( "Called" in line):
          print("\n\t> This should not happend =) !")
          break
        
        if( time_ref in line ):
          info_started = True

          # remove all empty block from split and take
          # the previous block if the current is "WALL"
          # because the previous is the time
          tmp = list(filter(None, line.split(" ")))
          for i in range(0, len(tmp)):

            if( tmp[i] == time_ref):
              # manage the fact that mm:ss could be used
              if('m' in tmp[i-1] ):
                tmp_2 = tmp[i-1].split('m')
                time_i = 60.0*(float(tmp_2[0]))
                time_i += float(tmp_2[1].replace('s',''))
              else:
                time_i = float(tmp[i-1].replace('s',''))

              break
          main_routines[tmp[0]] = [time_i,False]
          print("\t> Time for : "+tmp[0]+" = "+str(time_i)+" s")
      else:
        if( info_started ):
          break

    print("Main routines : ", main_routines)

    # now manage timing with hierarchy calls
    # get main routine which are the routine name after "writing output data .."
    # until first "called by " expression
    print(line)
    for line in fn:
      # print(line)
      line = line.replace("\n","")
      
      # skip empty line
      if( line.replace(" ","") !=  "" ):

        # we arrive to description of hierarchy of calls
        if( "Called by" in line):

          # get name of caller routine
          caller = line.replace(" ", "").split("Calledby")[1]
          caller = caller.replace(":", "")

          # FIX: *egterb -> to cegterg
          if( "*egterg" in caller ):
            caller = caller.replace("*","c")
          
          print("\t  > caller : ", caller)

          list_of_called = []
          for line in fn:

            ## WARNING: carreful if there is no space then it could mix up thing
            ##       add or "Called by" in line and manage to go one line back in fn
            if( line.replace("\n","").replace(" ","") == "" ):
              break
            else:
              if( time_ref in line ):
                tmp = list(filter(None, line.split(" ")))
                for i in range(0, len(tmp)):

                  if( tmp[i] == time_ref):
                    # manage the fact that mm:ss could be used
                    if('m' in tmp[i-1] ):
                      tmp_2 = tmp[i-1].split('m')
                      time_i = 60.0*(float(tmp_2[0]))
                      time_i += float(tmp_2[1].replace('s',''))
                    else:
                      time_i = float(tmp[i-1].replace('s',''))

                    break
                
                # add to the list of called routine for the current caller and a boolean
                # which is by default set to False. This value will be used
                # to describe if the current function is also a caller (ie node of calling
                # tree or just a leaf)
                list_of_called.append([tmp[0], False])

                # add his time and his skip value
                # skip=True, if time of routine less than 10% the time
                # spent in the caller
                skip = False
                caller_found = False
                time_in_caller = 0.0
                try:
                  time_in_caller = main_routines[caller][0]
                  caller_found = True
                except:
                  try:
                    time_in_caller = called_routines[caller][0]
                    caller_found = True
                  except:
                    print("\t\t\t> No time reference found for '"+caller+" !")
                
                if( caller_found ):
                  # print("Time reference of caller : " + str(time_in_caller))
                  if( threshold * time_in_caller > time_i ):
                    skip = True

                if( skip ):
                  print("\t\t> Time for : "+tmp[0]+" = "+str(time_i)+" s"+ " - SKIPPED !")
                else:
                  print("\t\t> Time for : "+tmp[0]+" = "+str(time_i)+" s")

                called_routines[tmp[0]] = [time_i, skip]
           
          hierarchy[caller] = list_of_called
        
        # if this is reached then we parse the entire file, normaly
        if( root in line ):
          nroot_found += 1
          tmp = list(filter(None, line.split(" ")))
          # get time info
          for i in range(0, len(tmp)):
            if( tmp[i] == time_ref):
              # manage the fact that mm:ss could be used
              if('m' in tmp[i-1] ):
                tmp_2 = tmp[i-1].split('m')
                time_i = 60.0*(float(tmp_2[0]))
                time_i += float(tmp_2[1].replace('s',''))
              else:
                time_i = float(tmp[i-1].replace('s',''))
          print("\n\t> Total wall time "+root+" : "+str(time_i)+" s")
          total_walltime = time_i
    
    print("\n\t> Warning 'General routines' & 'Parallel routines' skipped for now ! ")

  ## structure & timing
  print("\n\t> Main routines : ", main_routines)
  print("\n\t> Hierarchy of calls : ", hierarchy)
  print("\n\t> called_routines : ", called_routines)
  print("\n")

  ## some small test
  if( nroot_found > 1 ):
    print("\n> Something wrong : '"+root+"' found more than once")
  
  # if there is more than 1% difference between total walltime
  # and total time of sum(main routine) then time is missing somewhere
  # if( total_walltime > sum(main_routines.values())*1.01 ):
    # print("\n\t> Warning: total_walltime > sum(main_routines times) + 1% !")
    # print("\n\t\t> Time is missing somewhere !")
  
  # TODO: same check as before but with hierarchy

  # No longer a tuple, so data modification could happen !
  return [main_routines, called_routines, hierarchy, total_walltime]

## Filter times according to a cutoff 
## cutoff is a value ranging from 0.0 to 1.0 which correspond
## to the percent threshold of total time above which routine timing
## will be considered
##
def filter_times(times, cutoff):

  # total time is expected to be the last value also named
  # "PWSCF"
  total_walltime = 0.0
  try:
    total_walltime = times["PWSCF"]
  except:
    print("Error 'PWSCF' key not found !")
  
  cut_under = cutoff * total_walltime
  list_to_remove = []
  nroutines = len(times.keys())
  for k in times.keys():
    if( times[k] < cut_under ):
      list_to_remove.append(k)
  
  for i in list_to_remove:
    del times[i]
  
  print("\n\t  > Small time routine (<{}%) : {} out off {}".format(cutoff, len(list_to_remove), nroutines))

# Return the stacked according to one files_timing[i]
# return structure list of list made of [routine_name, bar_size, stat_offset]
#
# 'bars' list of small bar to display in the stacked bars
# 'datas' structure : list of dict [ main_routines, called_routine, hierarchy, totalWallTime]
# 'keys' string routine name to start recursion, ( a callar that calls routine )
# 'offset' start offset
# 'wbar' wbar value should decrease while recursion increase 
# 
# (recursive try)
#
# Start with : get_stacked_bars([], datas, main_routines[0], 0.0, wbar)
#
def get_stacked_bars(bars, datas, key, offset, wbar):

    print("Work with key : ", key)

    print("loop over : ", datas[2][key])
    # loop over called routine from key in hierarchy list
    for h_key in datas[2][key]:

      # if h_key should not be skipped (info given by called_routine[value, **boolean**])
      print("\t Check ", h_key[0], datas[1][h_key[0]] )
      if( not datas[1][h_key[0]][1] ):
        bars.append( [h_key[0], datas[1][h_key[0]][0], offset, wbar-0.1] )
        print("\t Updated Bars : ", bars, "\n")

        # if its a caller then go to the called routine
        if( h_key[1] ):
          get_stacked_bars(bars, datas, h_key[0], offset, wbar-0.1)
        offset += datas[1][h_key[0]][0]

## Utils functions
##
# Correct the boolean value of the heriarchy data
#
def correct_hierarchy(hierarchy):
  
  for k in hierarchy.keys():
    for val in hierarchy[k]:
      # try to set isCaller to True, if success then the called routine
      # will also be a caller =)
      try:
        tmp = hierarchy[val[0]]
        val[1] = True
      except:
        pass
  
  return hierarchy

# Assign colors to routine names also this function prevent assign colors to 
# two routines with the same name, obviously.
def assign_color(files_timing, old_timing_system):

  list_of_routines = []

  if ( old_timing_system ):
    # adjust colors to map with function name
    # if no function name is found then add unused colors
    for file_i in list_of_files:
      # add main routine
      list_of_routines += list(files_timing[file_i].keys())

  else:
    # adjust colors to map with function name
    # if no function name is found then add unused colors
    list_of_routines = []
    for file_i in list_of_files:

      # add main routine (element [0] of files_timing[file_i]) only if not skipped
      tmp_dict = files_timing[file_i][0]
      for k in tmp_dict.keys():

        # if skip value is set to False, then we need to keep the routine
        if( not tmp_dict[k][1] ):
          list_of_routines.append(k)

      # add called routine (element [1] of files_timing[file_i]) only if not skipped
      tmp_dict = files_timing[file_i][1]
      for k in tmp_dict.keys():

        # if skip value is set to False, then we need to keep the routine
        if( not tmp_dict[k][1] ):
          list_of_routines.append(k)

  print("\nAll routines names are: ", list_of_routines)

  # works for both old_timing_system and new one
  #
  # remove occurence in list since keys are unique in dict
  # and if more than one file, which will probably be the case 
  # almost every time 
  dict_routines =dict.fromkeys(list_of_routines)

  print("\nAll different routines names are : ", dict_routines.keys())

  # this should complains for now, since threshold on routine time
  # is not implemented yet
  n_diff_routines = len(dict_routines.values())
  if( n_diff_routines > len(lcolors) ):
    print("\n\t> Carrefull, there is more routines than colors !")

  # asign routine name to color
  color_i = 0
  for k in dict_routines.keys():
    if( color_i < len(lcolors) ):
      dict_routines[k] = lcolors[color_i]
    else:
      print("\n\t> Warning: routine '"+k+"' as no color assigned !")
    color_i += 1
  print("\n\t> Colors asignment : ", dict_routines)

  return dict_routines

## old timing system where everything is stacked no matter
## the hierarchy calls, this leads to redundancy of timing
## ie, total walltime != total bar size
old_timing_system = False

print("\n*****************************************")
print("* Benchmarks analysis & output parser ! *")
print("*****************************************")

num_of_args = len(sys.argv) - 1
print("\n > Number of args : %d" % num_of_args)

# create list of file to process, only files that exist or that
# were successfuly found !
list_of_files = []
for i in range(1,len(sys.argv)):
  if( os.path.exists(sys.argv[i]) ):
    list_of_files.append(sys.argv[i])
  else:
    print("\t> ***** Error with '" + sys.argv[i] + "' file not found !\n")

# get files information -----------------------------------------------------------
files_parallelism = {}
for i in list_of_files:
  files_parallelism[i] = run_info(i)[2]
  print("\n\t> file : '"+i+"' --> "+files_parallelism[i])

print("\n************************")
print("* Info for each file ! *")
print("************************\n")
# Get timing information ----------------------------------------------------------
at_least=0.10 # take into account only +10% of total time routines
files_timing = {}
for i in list_of_files:

  # get timing information - WALL time, could also be CPU
  if( old_timing_system ): 
    files_timing[i] = run_timing(i, "WALL")

    # remove low time consuming routines
    # files_timing[i] is a dict containing as keys routine name 
    # and as values the time spent in the routine 
    filter_times(files_timing[i], at_least)

    # sort all routine according to time consumption
    files_timing[i] = dict(sorted(files_timing[i].items(), key=lambda x:x[1]))

  else:

    # crazy new parsing to take hierarchy into account
    # add thresold value to 0.10 => 10 %
    files_timing[i] = run_timing_improved(i, "WALL", "PWSCF", at_least)
  
# Matplotlib graph ----------------------------------------

# files_timin is a dict, keys are files name
# each values are tuples (main_routines, called_routines, hierarchy, total_walltime)

print("\n*************************")
print("* Global info for graph *")
print("*************************\n")

# assign color to routine
routine_colors = assign_color(files_timing, old_timing_system)

if( not old_timing_system ):
  # correct the hierarchy boolean
  for file_i in list_of_files:
    print("\n> File ", file_i)
    print("\t> Initial hierarchy : ", files_timing[file_i][2], "\n")

    files_timing[file_i][2] = correct_hierarchy(files_timing[file_i][2])

    print("\t> Corrected hierarchy : ", files_timing[file_i][2], "\n")

# x axis index will be file name
index = np.arange(len(list_of_files))

# bar width
wbar = 0.55
bottom = 0
x = 0

print("\t> files timings : ")
for file_i in list_of_files:
  print(file_i, " : ", files_parallelism[file_i], " : ", files_timing[file_i])

# in case of multiple file, this prevent from having more than once each routine in
# the legend
all_ready_in_legend = dict.fromkeys(routine_colors.keys())
for k in all_ready_in_legend.keys():
  all_ready_in_legend[k] = False

fig,ax = plt.subplots()

if( old_timing_system ):
  index_x = 0
  for file_i in list_of_files:
    vals = list(files_timing[file_i].values())
    routine_names = list(files_timing[file_i].keys())
    icolor = 0
    offset = 0

    # len(vals)-1 in order to skip last value which is total walltime
    sc=plt.bar(0,0)
    for v in range(0,len(vals)-1):

      # manage proper legend
      if(not all_ready_in_legend[routine_names[v]] ):
        sc= plt.bar(index_x, float(vals[v]), width=wbar, color=routine_colors[routine_names[v]], \
                    bottom=offset, label=routine_names[v])
        all_ready_in_legend[routine_names[v]] = True
      else:
        sc= plt.bar(index_x, float(vals[v]), width=wbar, color=routine_colors[routine_names[v]], \
                    bottom=offset)

      # y_pos_text = vals[v]*0.5 + offset
      # plt.text(index_x, y_pos_text, routine_names[v])
      
      offset += vals[v]
      icolor += 1
    index_x += 1

else:

  print("\n\t> New plot system ACTIVE ")

  index_x = 0

  # usefull for annotate
  stacked_bar_dict={}

  for file_i in list_of_files:

    # set first element of bars to the first 'not skipped' element of main_routines
    # # bars = []
    # # for k in files_timing[file_i][0].keys():
    # #   if( not files_timing[file_i][0][k][1] ):
    # #     bars = [k, files_timing[file_i][0][k][0], 0.0]
    # #     print("\t> Set bars to : ", bars)
    # #     break
    
    # # if( len(bars) == 0 ):
    # #   print("This should not happen ! =)")
    
    # algo recursif sur chaque main routine
    bars = []
    offset = 0.0
    for k_main in files_timing[file_i][0].keys():
      # if main routine should not be skipped then
      # add his info + launch recursivity on its calls
      if( not files_timing[file_i][0][k_main][1] ):
        bars.append([k_main, files_timing[file_i][0][k_main][0], offset, wbar])
        get_stacked_bars(bars, files_timing[file_i], k_main, offset, wbar)
        offset += files_timing[file_i][0][k_main][0] 

    stacked_bar_dict[file_i] = bars

    sc=plt.bar(0,0) # hack to initialize the sc var before the loop

    # each of elem contains [routine_name, time value, offset, width of bar]
    for elem in bars:

      # check if routine is already in legend or not
      if( not all_ready_in_legend[elem[0]] ):
        sc= plt.bar(index_x, elem[1], color=routine_colors[elem[0]], width=elem[3], \
                    bottom=elem[2], label=elem[0])
        all_ready_in_legend[elem[0]] = True
      else:
        sc= plt.bar(index_x, elem[1], color=routine_colors[elem[0]], width=elem[3], \
                    bottom=elem[2])
    
    # index_x increase with file
    index_x += 1

# no matter if old_timing_system is True or False
plt.xticks(np.arange(0,len(list_of_files)), files_parallelism.values())
plt.ylabel("time (s)")
plt.xlabel("type of run")
title="AWSURF112 Benchmarks results of Q-E code - Ulysses"
title+= "\nCPU node: 2x16 cores Intel(R) Xeon(R) CPU E5-2640 0 @ 2.50GHz" 
#title+= "\nGPU node: 18 cores Intel Xeon E5-2697 v4 @ 2.30Ghz + Kepler K80"
plt.title(title)
# plt.subtitle("Hardware: CPU 2x18 cores Xeon Phi / node, GPU Kepler K80 ")

# add legend to graphs
if( old_timing_system ):
  color_legend = []
  for rn in routine_names[0:len(vals)-1]:
    color_legend.append(rn)

plt.legend()
print(files_parallelism)

# -------------- dynamique affichageeeuh, un peu de beaute dans ce bas monde --------------
annot = ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w"),
                    arrowprops=dict(arrowstyle="->"))
annot.set_visible(False)

def onclick(event):
    ix = int(round(event.xdata))
    iy = event.ydata

    # print("ixf = "+str(event.xdata)+ " -> " +str(ix))
    if( ix >= len(list_of_files) ):
      annot.set_visible(False)
      # print("Click on data from : " + list_of_files[ix])
    
    vals = list(files_timing[list_of_files[ix]].values())
    routine_names = list(files_timing[list_of_files[ix]].keys())
    offset = 0.0
    # print(iy)
    for v in range(0, len(vals)-1):
      # print("search between : "+str(offset)+" and "+str(offset+vals[v]))
      if( iy > offset and iy < offset+vals[v] ):
        annot.xy = (event.xdata,event.ydata)
        annot.set_text(routine_names[v]+":"+str(vals[v])+"s")
        annot.get_bbox_patch().set_alpha(0.4)
        annot.set_visible(True)

        fig.canvas.draw_idle()
        break
      offset += vals[v]

def onclick_new(event):
    ix = event.xdata
    iy = event.ydata

    # do anything but clear the bbox if click outside the axis
    if( ix is None or iy is None ):
      annot.set_visible(False)
      fig.canvas.draw_idle()
      return

    file_i = int(round(ix))
    annot_msg = ""
    if( file_i < len(list_of_files) ):
      annot_msg = "Total Walltime: "
      annot_msg += str(round(files_timing[list_of_files[file_i]][3],2))
      annot_msg += " s"
    
      # add info of main routine only
      # for hkey in files_timing[list_of_files[file_i]][0]:

      #   # not skipped main routines
      #   if( not files_timing[list_of_files[file_i]][0][hkey][1] ):
      #     annot_msg += "\n" + hkey + " : "
      #     annot_msg += str(files_timing[list_of_files[file_i]][0][hkey][0])
      #     annot_msg += " s"

      # look for the main routine in the superior offset
      main_routine_is = ""
      max_val = 0.0
      min_val = 0.0
      bloc_val = 0.0
      for elem in stacked_bar_dict[list_of_files[file_i]]:
        
        # print(iy, " vs ", elem[2], " iy is ", type(iy), " elem[2] is ", type(elem[2]))

        if( iy > elem[2] ):
          # print("looking @ ", elem[0])
          try:
            tmp = files_timing[list_of_files[file_i]][0][elem[0]]
            main_routine_is = elem[0]
            min_val = elem[2]
            max_val= elem[1] + elem[2]
            bloc_val = elem[1]
            # print("\n> main routine is : ", main_routine_is)
          except:
            pass
      
      # make annot with contained bars
      # add main routine 
      annot_msg += "\n"+ main_routine_is + " : " + str(round(bloc_val,2)) + " s "
      for elem in stacked_bar_dict[list_of_files[file_i]]:
        if( elem[2] >= min_val ):
          if( (elem[2]+elem[1]) < max_val ):
            annot_msg += "\n" + elem[0] + " : "
            annot_msg += str(round(elem[1],2)) + " s"

      
    annot.xy = (event.xdata,event.ydata)
    annot.set_text(annot_msg)
    annot.get_bbox_patch().set_alpha(0.3)
    annot.set_visible(True)

    fig.canvas.draw_idle()
# -----------------------------------------------------------------------------------------

if ( old_timing_system ):
  cid = fig.canvas.mpl_connect('button_press_event', onclick)
else:
  cid = fig.canvas.mpl_connect('button_press_event', onclick_new)
plt.show()
