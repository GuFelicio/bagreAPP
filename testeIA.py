import google.generativeai as genai

# Use a sua chave aqui
genai.configure(api_key="AIzaSyDYjPdILeBUvZwRSgtptvpu5ao1Wy_8vNM")

print("🔍 Listando modelos disponíveis para sua chave:")
for m in genai.list_models():
  if 'generateContent' in m.supported_generation_methods:
    print(f"- {m.name}")