FROM python:3.11.3
ENV EMSDK=/opt/emsdk EMSDK_NODE=/opt/emsdk/node/16.20.0_64bit/bin/node \
    PATH=/opt/emsdk:/opt/emsdk/upstream/emscripten:/opt/emsdk/node/16.20.0_64bit/bin:$PATH
RUN git clone https://github.com/emscripten-core/emsdk.git $EMSDK &&\
    emsdk install 3.1.46 && emsdk activate 3.1.46 &&\
    pip install pyodide-build==0.25.0 &&\
    python -c "from pyodide_build.build_env import init_environment; init_environment()"

RUN pyodide build zengl -o /web/
COPY game /game
RUN pyodide build /game -o /web/ --exports pyinit
COPY audio /audio
RUN pyodide build /audio -o /web/

COPY public /web
CMD python -m http.server -d web
# CMD bash
