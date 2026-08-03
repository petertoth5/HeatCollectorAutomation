def read_and_convert(file_path):
    try:
        with open(file_path) as file:
            text = file.read()
            value = float(text.strip())
            return value
    except ValueError:
        print("Error: unable to convert text to a floating-point number.")
        return None

def write_value(tempOffset, file_path):
    try:
        with open(file_path, 'w') as file:
            file.write(str(tempOffset))
        print(f"tempOffset {tempOffset} written to {file_path}")
    except Exception as e:
        print(f"Error writing value: {e}")

def compute_corrected_offset(reference_temp, current_avg_temp, old_offset):
    return old_offset + (reference_temp - current_avg_temp)
