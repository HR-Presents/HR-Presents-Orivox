import uvicorn
from orivox.config import HOST,PORT
if __name__=="__main__": uvicorn.run("orivox.app:app",host=HOST,port=PORT,reload=False)
