from sec_edgar_downloader import Downloader
import os
import re
from bs4 import BeautifulSoup
import textwrap

import google.generativeai as genai

# from IPython.display import display
from IPython.display import Markdown

# path = "./download_files/sec-edgar-filings/"
## Input Google API Key
GOOGLE_API_KEY = 'YOUR GOOGLE API KEY'

def download_data(ticker, path = "./download_files"):
    """
    Function to download the data from the SEC site in human readable format (which will be present in primary-document.html)
    Args:
        ticker (str) : The name of the company filings to download
        path (str) : the path where this data is downloaded
    Return:
        (bool) : if the download worked or not. False generally means that the company does not exist.
    """
    dl = Downloader("GTARC", "agupta886@gatech.edu", path)
    try:
        dl.get("10-K", ticker, download_details = True)
        return True
    except:
        return False

## We save the downloaded data to ./download_files/sec-edgar-filings/<ticker>
## Test downloads
# download_data("TSLA", "./download_files")
# download_data("AAPL", "./download_files")


def return_dataparsed(path, option):
    """
    Function that returns human readable data by parsing through the human readbale HTML provided by the downloader
    Args:
        path (str) : The path of the .html file to parse through
        option (str) : fast analyses less data while slow analyses more data.
    Return:
        parsed_data (str) : The html file converted to text that can be fed into the LLM
    """
    file = open(path, "r")
    data = file.read()
    file.close()
    parsed_data = BeautifulSoup(data, features="html.parser")
    
    # ret_data = ' '.join(parsed_data.get_text().split())
    if option == "general":
        ret_data = parsed_data.get_text()
        ret_data = re.sub(r'[^\x00-\x7F]+', '', ret_data)
        ret_data = " ".join(ret_data.split()).lower()
        idx_pt1 = ret_data.find("ITEM 1.".lower())
        ret_data = ret_data[idx_pt1 + 10 :]
        idx_pt1 = ret_data.find("ITEM 1.".lower())
        ret_data = ret_data[idx_pt1 :]
        idx_pt2 = ret_data.find("PART II".lower())
        parsed_data = ret_data[0 : idx_pt2]
        ret_data = ret_data[idx_pt2 + 8: ]
        idx_pt3 = ret_data.find("PART III".lower())
        idx_pt4 = ret_data.find("PART IV".lower())
        parsed_data += ret_data[idx_pt3 : idx_pt4]
        return parsed_data
    elif option == "financial":
        ret_data = parsed_data.get_text()
        ret_data = re.sub(r'[^\x00-\x7F]+', '', ret_data)
        ret_data = " ".join(ret_data.split()).lower()
        idx_pt1 = ret_data.find("ITEM 1.".lower())
        ret_data = ret_data[idx_pt1 + 10 :]
        idx_pt1 = ret_data.find("ITEM 1.".lower())
        ret_data = ret_data[idx_pt1 :]
        idx_pt2 = ret_data.find("Item 6.".lower())
        ret_data = ret_data[idx_pt2 + 8: ]
        idx_pt3 = ret_data.find("item 9.".lower())
        parsed_data = ret_data[0 : idx_pt3]
        return parsed_data
    else :
        ret_data = parsed_data.get_text()
        ret_data = re.sub(r'[^\x00-\x7F]+', '', ret_data)
        ret_data = " ".join(ret_data.split()).lower()
        idx_pt1 = ret_data.find("ITEM 1.".lower())
        ret_data = ret_data[idx_pt1 + 10 :]
        idx_pt1 = ret_data.find("ITEM 1.".lower())
        ret_data = ret_data[idx_pt1 :]
        idx_pt2 = ret_data.find("PART II".lower())
        parsed_data = ret_data[0 : idx_pt2]
        ret_data = ret_data[idx_pt2 + 8: ]
        idx_pt3 = ret_data.find("PART III".lower())
        idx_pt4 = ret_data.find("PART IV".lower())
        parsed_data += ret_data[0 : idx_pt4]
        return parsed_data

##Example usage
# print(return_dataparsed("full-submission.txt"))

def read_files_in_subdirectory(ticker, directory = "./download_files/sec-edgar-filings/"):
    """
    Function to read all the human-readable HTML files to create input data for the LLM model.
    Args:
        ticker (str) : The name of the company filings to download
        directory (str) : The source directory where the filings for this ticker will be found
    """
    directory += ticker + "/"
    file_paths = []
    # Iterate over all files and subdirectories in the given directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Check if the file has a .txt extension
            if file.endswith(".html"):
                # Construct the full path to the file
                file_path = os.path.join(root, file)
                # Read the contents of the file and append it to the list
                file_paths.append(file_path)
    return file_paths

## Example usage
# file_paths = read_files_in_subdirectory("MSFT")
# for i in file_paths:
#     print(i)

# def to_markdown(text):
#     text = text.replace('•', '  *')
#     return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

def send_parts(model, part, k = 10000):
    """
    Generate the summaries from the model.
    Args :
        model : The model that is being used.
        part : The text that needs to be summarized in parts (as model cannot take it all at once).
    Return :
        summary (str) : The summary generated by the model.
    """
    split = part.split()
    summary = ""
    for i in range(len(split)//k):
        s = " ".join(split[i * k : (i+1)*k])
        for i in range(10):
            try:
                r = model.generate_content("Summarize and analyse the growth for the following:\n" + s)
                if r.text:
                    summary += r.text
                    break
            except:
                continue
    return summary

def llm_prompt(file_paths, ticker, option):
    """
    Given an input, this function passes the input to the llm and generates a response. We use gemini-pro for the response.
    Args :
        file_paths (list) : A list of file_paths to the .html file
        ticker (str) : The ticker requested
        optione (str) : fast or slow processing
    Return :
        response : the final response generated by the LLM
    """

    genai.configure(api_key=GOOGLE_API_KEY)

    y = 0
    model = genai.GenerativeModel('gemini-1.0-pro')
    final_text = ""
    k = 10000

    
    for file_path in file_paths:
        try:
            part1 = return_dataparsed(file_path, option)
            response = send_parts(model, part1, k)
        except:
            pass
        for i in range(10):
            try:
                response = model.generate_content(f"Summarize these in a few paragraphs:\n" + response).text
                break
            except:
                pass
        y += 1
        print(y)
        final_text += response
    
    
    # inp_txt = return_dataparsed(file_paths[0])
    # response = chat.send_message(inp_txt) 
    if option == "general":
        text1 = f"Summarize the following in a page and analyse the advancement of the company:\n"
    else:
        text1 = f"The following are 10-K filing summaries of each year of {ticker}. Give the growth of the company, the summary and some interesting facts about the company in a few paragraphs for each:\n"

    final_text = text1 + final_text
    print("llm response generating.....")
    for i in range(10):
        try:
            response = model.generate_content(final_text)
            break
        except:
            pass
    return response

def generate_insights(ticker, option = 'financial'):
    """
    Function to combine all the functions before and generate a response
    Args :
        ticker (str) : The company ticker
        option (str) : fast or slow processing
    Return:
        response : the final response generated by the LLM
    """
    
    downloaded = download_data(ticker)
    ## Check if successful
    if not downloaded:
        raise ValueError("The ticker input is incorrect. Please try correct ticker.")
    else:
        print("10-K data downloaded, continuing to processing.....")
    file_paths = read_files_in_subdirectory(ticker)
    
    print(f"{len(file_paths)} year(s) of data being processed.....")

    ## llm functionality
    response = llm_prompt(file_paths, ticker, option)

    return response
