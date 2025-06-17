import random


def guess_number_game(min_val=1, max_val=100, max_attempts=7):
    """
    Консольна гра "Вгадай число".

    Параметри:
    - min_val: мінімальне можливе число (включно)
    - max_val: максимальне можливе число (включно)
    - max_attempts: кількість спроб гравця
    """
    secret = random.randint(min_val, max_val)
    print(
        f"Вітаю! Я загадав число від {min_val} до {max_val}. Спробуйте вгадати його за {max_attempts} спроб.")

    for attempt in range(1, max_attempts + 1):
        while True:
            try:
                guess = int(input("Введіть ваше припущення: "))
                break
            except ValueError:
                print("Будь ласка, введіть ціле число.")

        if guess < secret:
            print("Занадто маленьке!")
        elif guess > secret:
            print("Занадто велике!")
        else:
            print(f"Ви вгадали! Це число {secret}.")
            return

    # Якщо всі спроби вичерпані
    print(
        f"На жаль, ви не вгадали. Я загадав число {secret}. Спробуйте ще раз пізніше!")


def main():
    guess_number_game()


if __name__ == "__main__":
    main()
