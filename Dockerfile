
FROM python:3.13


WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando padrão para iniciar o bot
CMD ["python", "-m", "app.bot.main"]