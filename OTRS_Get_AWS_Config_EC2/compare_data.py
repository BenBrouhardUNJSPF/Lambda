import boto3
import datetime
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta


def compare_data(table_name, today_str,  nametag , offset=1,):
    """
    Compare data from a DynamoDB table for two different dates.

    Args:
    table_name (str): The name of the DynamoDB table to query.
    today_str (str): The date for the "today" query, in the format 'YYYY-MM-DD'.
    yesterday_str (str): The date for the "yesterday" query, in the format 'YYYY-MM-DD'.
    nametag (str): The nametag to search for in the data.

    Prints a message indicating whether the rows from today and yesterday are the same or different.
    """
    # Create a DynamoDB resource
    dynamodb = boto3.resource('dynamodb')

    # Get the table
    table = dynamodb.Table(table_name)
    
    
        # Calculate the date for the "yesterday" query
    today = datetime.strptime(today_str, '%Y-%m-%d')
    yesterday = today - timedelta(days=offset)
    print(yesterday)
    yesterday_str = yesterday.strftime('%Y-%m-%d')

    # Scan the table for today's data
    response_today = table.scan(
        FilterExpression=Attr('recorded_date').eq(today_str) & Attr('nametag').eq(nametag)
    )

    # Scan the table for yesterday's data
    response_yesterday = table.scan(
        FilterExpression=Attr('recorded_date').eq(yesterday_str) & Attr('nametag').eq(nametag)
    )
    #print(response_today, response_yesterday)
        # Check that both rows have data
    # if not response_today['Items'] or not response_yesterday['Items']:
    #     print("One or both of the rows do not have data.")
    #     return False

    # Remove the 'date' column from the results
    for item in response_today['Items']:
        item.pop('recorded_date', None)
    for item in response_yesterday['Items']:
        item.pop('recorded_date', None)

    # Compare the results
    if response_today['Items'] != response_yesterday['Items']:
        print(f"\nThe rows from {today} and {yesterday} are different.\n")
        print("Today's rows:\n")
        print(response_today['Items'])
        print("\nYesterday's rows:\n")
        print(response_yesterday['Items'])
        return True
    else:
        print(f"The rows from {today} and {yesterday} are the same.")
        return False
    
    