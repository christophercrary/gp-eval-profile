# GP Evaluation Profiling
This repository provides a means to profile (i.e., benchmark) the evaluation methodologies given by some genetic programming 
(GP) tools. The evolutionary mechanisms provided by the GP tools 
are *not* included when profiling——only mechanisms for calculating
"fitness."

This repository was originally created for the paper 
"Work-in-Progress: Toward a Robust, Reconfigurable Hardware
Accelerator for Tree-Based Genetic Programming," by Crary et al., 
which compared the evaluation performance of an initial FPGA-based GP hardware accelerator with that of the GP software tools *DEAP* (version 1.3), *TensorGP* (Git revision d75fb6), and *Operon* (Git revision 9e7ee4).

## Included Tools

A means for profiling for the following GP tools is given:

- [DEAP](https://github.com/DEAP/deap) - for the original paper, 
click [here](http://vision.gel.ulaval.ca/~cgagne/pubs/deap-gecco-2012.pdf).
- [TensorGP](https://github.com/AwardOfSky/TensorGP) - for the original paper,
click [here](https://cdv.dei.uc.pt/wp-content/uploads/2021/04/baeta2021tensorgp.pdf).
- [Operon](https://github.com/heal-research/operon) - for the original paper,
click [here](https://dl.acm.org/doi/pdf/10.1145/3377929.3398099).


## Profiling
By default, the repository already contains the results
published in the aforementioned paper, "Work-in-Progress: Toward a Robust, 
Reconfigurable Hardware Accelerator for Tree-Based Genetic Programming."
These results are contained in the `experiment/results` directory and
can be viewed by running the `experiment/tools/stats.ipynb` Jupyter Notebook file.

If so desired, after successfully completing installation, you may run 
the entire profiling suite by executing the following within a shell 
program, after having navigated to the repository directory within the shell:

```
cd experiment
bash run.sh
```

After the `run.sh` script fully executes, to view some relevant statistics, run the Jupyter Notebook file given by the path `experiment/tools/stats.ipynb`.

## Installation instructions

The following has been verified via Ubuntu 20.04 and CentOS 7. It is likely that other Linux distributions are supported, and it is plausible that Windows operating systems are supported, but it is unlikely that MacOS is readily supported.

### Prerequisites
- Ensure that some Conda package management system 
(e.g., [Miniconda](https://docs.conda.io/en/latest/miniconda.html)) 
is installed on the relevant machine.
- Clone this repository onto the relevant machine.

Upon cloning the repository, set up the relevant Conda environment
and tools by executing the following within
a shell program, after having navigated to the repository directory
within the shell:

```
conda env create -f environment.yml
conda activate gp-eval-profile
bash install.sh
```
