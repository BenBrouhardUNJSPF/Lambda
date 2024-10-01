import boto3
from botocore.exceptions import BotoCoreError, ClientError



SINGLE_LINE_LENGTH = 80
DOUBLE_LINE_LENGTH = 47
#FOOTER_TEXT = os.environ['AdditionalEmailFooterText']
FOOTER_TEXT= "sent from AWS"
HEADER_TEXT = 'UNJSPF Report \n'
FOOTER_URL = 'https://console.aws.amazon.com/securityhub/home/standards#/standards'

def send_email(subject, body, from_addr, to_addr):
    ses_client = boto3.client('ses')
    try:
        response = ses_client.send_email(
            Source=from_addr,
            Destination={
                'ToAddresses': to_addr
            },
            Message={
                'Subject': {
                    'Data': subject
                },
                'Body': {
                    'Html': {
                        'Data': body
                    }
                }
            }
        )
    except (BotoCoreError, ClientError) as error:
        print(f'Failed to send email: {error}')
        return False

    return True

def add_horizontal_line(text_body, line_char, line_length):
    """
    Adds a horizontal line to the given text body.

    Args:
        text_body (str): The text body to which the horizontal line will be added.
        line_char (str): The character used to create the horizontal line. Example: '-' or '='.
        line_length (int): The length of the horizontal line.

    Returns:
        str: The updated text body with the horizontal line added.
    """
    y = 0
    while y <= line_length:
        text_body += line_char
        y += 1
    text_body += '\n'
    
    return text_body



def create_table(columns, rows, title='',width=50):
    """
    Create a formatted table with the given columns, rows, and title.

    Args:
        columns (list): A list of column names.
        rows (list): A list of dictionaries representing the rows of the table.
        title (str): The title of the table.

    Returns:
        str: The formatted table as a string.

    """
    len_rows = len(rows)
    SINGLE_LINE_LENGTH = width
    table =  '<div>\n\t' + title + ': '
    # add the count of findings
   
    #table += add_horizontal_line('', '-', SINGLE_LINE_LENGTH)
    
    table += '<table>\n\t\t<thead>\n\t<tr>' 
    # Add column names
    for column in columns:
        
        table += '\t\t<th>' + column + '</th>\n'
    table += '</tr>\n\t</thead>\n\t\t<tbody>\n'
    #table += add_horizontal_line('', '-', SINGLE_LINE_LENGTH)
    
    i = 0
    while i < len_rows:

        table += '\t<tr>\n'
        for column in columns:
            table += '\t\t<td>' + str(rows[i].get(column, '')) + '</td>\n'
        table += '\t</tr>\n'
        i += 1
    
    table += '<tr class="tfoot" > Count: ' + str(len_rows) + '\n<tr>'
    table += '\t\t</tbody> \n\t </table>\n</div><br>\n\n'


    # # Add findings
    # for row in rows:
    #     for column in columns:
    #         table += str(rows[0]) + '\t\t'
    #     table += '\n'
    
    # while len(table) < width:
    #     table += '\n'
    
    #     #table += add_horizontal_line('', '-', SINGLE_LINE_LENGTH)
    #     table += '\n'
    
    return table

def create_html_header(header_text):
    header = '''<html><head>

                                    <style>
                                h3 {
                                font-family: 'Asul', sans-serif;
                                font-size: 12px;

                                color: #1C6EA4; 
                                }

                                table 
                                { width:90%
                                /*border-collapse: collapse; 
                                background: #f9f9f9;*/
                                font-family: 'Asul', sans-serif;
                                font-size: 12px;
                                color: #034575;
                                border-bottom: 2px solid #1C6EA4;
                                margin-left: auto; 
                                margin-right: auto;
                                

                                }



                                th {
                                padding: 10px;
                                padding-bottom: 3px;
                                text-align: left;
                                background: #A2D2f9;
                                color: #1C6EA4;
                                border-bottom: 2px solid #1C6EA4;
                                }

                                th:first-child {
                                border-top-left-radius:12px;
                                }
                                
                                th:last-child {
                                border-top-right-radius:12px;
                                border-right:none;
                                }

                                td {text-align: center;
                                /* border-bottom: 1px solid #ddd;*/
                                padding: 3px;
                                }



                                .odd  { background-color:#ffffff; }

                                .even { background-color:#D0E4F5; }

                                .tfoot {
                                    font-size: 14 px;
                                    font-weight: bold;
                                    color: #1C6EA4;
                                    background: #D0E4F5;
                                    border-top: 3px solid #444444;
                                }

                                .dataTables_info { margin-bottom:4px; }

                                .sectionheader { cursor:pointer; }

                                .sectionheader:hover { color:red; }
                                .red { color:red; }
                                .green { color:green; }
                                    
                                    
                                    
                                    </style>\n
                                    \t\n</head>
                                    \t\t\n<body>\n'''
    header += '<h3>' + HEADER_TEXT + '</h3>\n<br>\n'
    return header

def create_html_footer(footer_text=None, footer_url=None):
    footer = '<div class="tfoot"> ' + footer_text 
    if footer_url:
        footer += '\n<br><a href="' + footer_url + '">' + footer_url + '</a>'
    footer += '\n\t</div>\n\t</body></html>'
    return footer