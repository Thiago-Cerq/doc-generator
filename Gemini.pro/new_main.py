```
```
import sys

# This function takes a list of numbers and returns the sum of all the numbers in the list.
def sum_numbers(numbers):
  """
  This function takes a list of numbers and returns the sum of all the numbers in the list.

  Args:
    numbers: A list of numbers.

  Returns:
    The sum of all the numbers in the list.
  """

  total = 0
  for number in numbers:
    total += number
  return total


# This function takes a list of numbers and returns the average of all the numbers in the list.
def average_numbers(numbers):
  """
  This function takes a list of numbers and returns the average of all the numbers in the list.

  Args:
    numbers: A list of numbers.

  Returns:
    The average of all the numbers in the list.
  """

  total = sum_numbers(numbers)
  return total / len(numbers)

if __name__ == "__main__":
  # Get the list of numbers from the command line.
  numbers = [int(number) for number in sys.argv[1:]]

  # Print the sum and average of the numbers.
  print("The sum of the numbers is", sum_numbers(numbers))
  print("The average of the numbers is", average_numbers(numbers))
```