import csv
def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        if line is None:
            yield ''
        else:
            yield line.encode('utf-8')
        
def export_events(events, out_file, user=None, encoding='utf-8'):
    writer = csv.writer(out_file)
    writer.writerow([
          'Event', 'Date', 'Days', 'Hours', 'Description'
          ])

    total_days = total_hours = 0
    
    for event in events:
        row = [
          event['title'],
          event['start'].strftime('%Y-%m-%d')     
        ]
        if event['all_day']:
            days = event['end'] - event['start']
            row.append(str(days.days + 1))
            total_days += days.days + 1
            row.append('')
        else:
            row.append('')
            hours = (event['end'] - event['start']).seconds / 3600.0
            row.append(str(round(hours, 1)))
            total_hours += hours
        row.append(event['description'])
        writer.writerow(list(utf_8_encoder(row)))
    row = ['TOTAL:', '', str(total_days), str(total_hours), '']
    writer.writerow(row)
            
            
        