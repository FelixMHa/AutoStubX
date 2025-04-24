
def is_ascii_printable(s):
    s = str(s)
    is_ascii = all(32 <= ord(char) <= 126 for char in s)

    # make sure it's not backwars slash (\) as they can cause issues
    is_backwards_slash = '\\' in s

    return is_ascii and not is_backwards_slash

def find_two_with_different_output(training_data):

    output1 = training_data[0]['output']
    for i in range(1, len(training_data)):
        if training_data[i]['output'] != output1:
            return training_data[0], training_data[i]
    return None, None