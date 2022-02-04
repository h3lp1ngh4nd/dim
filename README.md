# Delegate Incoming Monitor (DIM) - fixed for Liskv3
A tool to collect data from all blocks forged by a delegate in a certain time period in BTC/USD/EUR at the time of forging. 
Useful for tax purposes, for example.

## Usage
DIM can be run "as-is" in interactive mode, or with optional arguments.

#### Interactive Mode
Open `dim.exe` and follow the instructions.

#### Arguments
DIM accepts multiple (optional) arguments. Examples are:

`dim.exe --network testnet --address lsknp3rrhgbgev5kxxmvja8ct35yahhduwdosaj9w`

`dim.exe --network mainnet --address lskq3mtp4vkzc32nqbod9nfyzhbwwzfnswasrtor6 --share 60 --start 2021/09/01 --end 2021/09/10`

For a complete list, please see:
``` .\dim.exe -h

optional arguments:
  -h, --help            show this help message and exit
  --network {mainnet,testnet,custom}
                        use 'mainnet' or 'testnet'
  --address ADDRESS     specify delegate address
  --share SHARE         specify voter's share
  --start START         specify start date (yyyy/mm/dd)
  --end END             specify end date (yyyy/mm/dd)
```  
#### Running the Python script
You can run the original Python script if that's preferred. 
The only non-standard library used is `requests`, found in the `requirements.txt` file. 
All of the above instructions still apply to using this method.
