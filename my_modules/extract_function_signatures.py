import os
import re

def extract_signatures(source_folder, output_file):
    class_signature_pattern = re.compile(r'^class\s+\w+')
    function_signature_start_pattern = re.compile(r'^\s*def\s+\w+\(')
    function_signature_end_pattern = re.compile(r'.*\)\s*->\s*[\w\[\], ]+\s*:$|.*\):$')
    decorator_pattern = re.compile(r'^\s*@[\w\.]+\(')

    with open(output_file, 'w') as outfile:
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                if file.endswith('.py'):
                    outfile.write(f"# {file}\n")  # Write file name
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as infile:
                        inside_class = False
                        multiline_function_def = ""
                        decorator_line = ""
                        for line in infile:
                            if decorator_pattern.match(line):
                                decorator_line = line.strip()
                                continue
                            if multiline_function_def:
                                multiline_function_def += " " + line.strip()
                                if function_signature_end_pattern.match(multiline_function_def):
                                    indent = '    ' if inside_class else ''
                                    function_def = (decorator_line + "\n" + indent + multiline_function_def) if decorator_line else (indent + multiline_function_def)
                                    outfile.write(function_def + '\n')
                                    multiline_function_def = ""
                                    decorator_line = ""
                                    continue
                            elif function_signature_start_pattern.match(line):
                                multiline_function_def = line.strip()
                                if function_signature_end_pattern.match(line):
                                    indent = '    ' if inside_class else ''
                                    function_def = (decorator_line + "\n" + indent + multiline_function_def) if decorator_line else (indent + multiline_function_def)
                                    outfile.write(function_def + '\n')
                                    multiline_function_def = ""
                                    decorator_line = ""
                                    continue
                            elif class_signature := class_signature_pattern.match(line):
                                inside_class = True
                                outfile.write(class_signature.group() + '\n')
                    outfile.write('\n')  # Add an empty line after each file

# Example usage
extract_signatures('.', 'function_signatures.txt')