# VR-Arch

This repository encapsulates several modules that work in unison with BIM data (Building Information Modeling):

 * *Sandbox*: A custom Unreal Engine sandbox where BIM files can be loaded.
 * *Python API*: This API enables interactions with the sandbox.
 * *Neo4j Server*: We convert BIM graphs into Neo4j graphs in order to query information using Cypher.

 * ***VR-Arch***: Our proposed agentic system that processes iteratively user commands, using different tools depending on the query itself. 
   - *Modifier tool*: This tool generates Python code following the previously mentioned Python API, enabling changes on the BIM representation of the sandbox.
   - *Querier tool*: The querier generates Cypher code that is executed in the Neo4j server, accessing the metadata stored in the graph and retrieving the needed answer.
   - *ID retriever tool*: If the user wants to retrieve information about a specific object, this tool manages to find it and retrieve its ID, so that in the next iteration VR-Arch is able to generate cypher code of that specific object.

<p align="center">
    <img src="assets/react_router.png" alt="VR-Arch." width="80%"/>
</p>

The proposed system is described in the paper titled "A Virtual Assistant for Architectural Design in a VR Environment". It is currently under evaluation and the current version can be found as a PDF in this repository. 

## Running the sandbox

The first thing you should do after cloning the repository is to download the sandbox and set everything up correctly to get it running. Depending on your OS, you will download different executables, the options being [Windows](https://drive.google.com/file/d/1JxPCLwUEc7SMMcnlmJBXcaxH3iVgGZtj/view?usp=sharing) and [Linux](https://drive.google.com/file/d/1-MwG-NxYy9ccYPKLMqlLaKPm37kC9ujC/view?usp=sharing). We recommend to unzip it under src/sandbox in order to keep things under control.

For Windows users, just execute `src/sandbox/Windows/Luminous.exe` to get the sandbox running. For Linux users, open the command line and execute the Luminous.sh found in the zip file: `sh src/sandbox/Linux/Luminous.sh`.

In any case, the sandbox will be empty with no building at all in sight. This is expected, as buildings are loaded using the Python API:

<p align="center">
    <img src="assets/empty_sandbox.png" alt="Empty sandbox." width="49%"/>
</p>


## Installing dependencies

### Python >=3.11

It is necessary to work with Python 3.11 or more. You are free to use Conda or Pip, but explanations focus on Pip. To install the minimum requirements to run the repository, you first need to install the dependencies found in `requirements.txt` with `pip install -r requirements.txt`.

**Note**: Apart from those dependencies, you will also need to install the package `ìfcopenshell`. Unfortunately, sometimes installing it via pip gives an error, so you will need to enter on this [link](https://docs.ifcopenshell.org/ifcopenshell-python/installation.html), go to the ZIP packages section, and follow the instructions there to install it manually.

### Java 17

TBD


### Sandbox IFC Loader 

Finally, in order to load .ifc files into the Sandbox, you need to download a file and locate it under 'src/luminous'. In the case of Windows devices this file will be [IfcConvert.exe](https://drive.google.com/file/d/1uC-7S6LgioBF-WLwtBklamXlc0_FAW0e/view?usp=sharing) whereas for Linux it will be [IfcConvert.elf64](https://drive.google.com/file/d/1n_rtzLPNKvLXFccLlKLprTNPdvVDLQ3p/view?usp=sharing).


## Neo4j server

TBD

## VLLM server

TBD

## Main Script: *main.py*

This script is prepared to connect to the sandbox and the Neo4j server, and execute code generated with LLMs. This means that there are three things to be done before running the script:

 1) Run the sandbox (as specified above).
 2) Start the Neo4j server.
 2) Run the VLLM server, either on your device or a server (follow the example at `scripts/vllm_start_router.slurm`).

To run the script, execute the following:

```
python main.py --config CONFIG_FILE 
```

The configuration is specified in config.yaml, where you can specify different input parameters. You can find examples in They are divided into six groups:

 * *sandbox*: you can specify the IFC file to be loaded in the sandbox and the IP address and port in which the sandbox is listening (127.0.0.1:9999 by default).
 * *helperLLM*: when using a VLLM server, you will need to specify the model name and the API's URL and key to connect to that specific LLM (which are set when initializing the server).
 * *cypherLLM*: TBD
 * *neo4j*: TBD
 * *agent*: TBD
 * *voiceLayer*: you can specify the api URL and key, along an input argument that controls whether partial audios are transcribed or not. 

For this script, the *voiceLayer* is optional. However, you don't need to remove its content in the config file if you are not using it.

Once it is executed, you will be prompted to give an instruction. For example, given "Hide all walls in sight", the scene in the sandbox would change in the following manner:

<p align="center">
    <img src="assets/house_with_walls.png" alt="House with walls." width="47%"/>
    <img src="assets/house_without_walls.png" alt="House with walls." width="47%"/>
</p>

If you enter an empty string, the voice layer will be activated, your microphone will record during 5 seconds whatever you say and it's going to transcribe it via the voice layer. However, you need a server with a valid key to use it. Moreover, a second inference by the LLM is done to give a verbal feedback to the user. If the sandbox is focused just after the execution of the code, you will hear it as an audio.

**Note:**: The code is prepared for a private WSS server that is not provided, so minor changes might be needed to adapt the code to another WSS server. Changes should be made in `src/voice_layer.py`.


## Python API

The Sandbox script is prepared to generate Python code that follows a custom API. You won't need to write the code itself, but it is good to have a general gist. You can find it inside `src/luminous`.

The connection with the sandbox is done with the following code. 

```
from src.luminous.luminous import Luminous

l = Luminous()
```

In order to load a building into the scene, and IFC object is loaded:

```
from src.luminous.luminous_ifc import IFC

ifc = IFC(l.load_ifc(ifc_filename))
```

When the LLM generates the code, it takes these variables into account, as if `l` and `ifc` were already instantiated. You can play with the functions found in the API freely. You can check `src/prompting/sandbox_prompts.py` for the documentation (`API_DOCS`) and a few examples (`API_EXAMPLES`).


