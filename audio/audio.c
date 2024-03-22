#include <Python.h>
#include <structmember.h>

#define QOA_IMPLEMENTATION
#define QOA_NO_STDIO
#include "qoa.h"

extern int audio_load_audio(short * data, int size);
extern void audio_play_audio(int audio, int loop);

static PyObject * meth_load_audio(PyObject * self, PyObject * args, PyObject * kwargs) {
    const char * keywords[] = {"data", NULL};

    PyObject * data;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O!", (char **)keywords, &PyBytes_Type, &data)) {
        return NULL;
    }

    return PyLong_FromLong(audio_load_audio((short *)PyBytes_AsString(data), (int)PyBytes_Size(data) / 2));
}

static PyObject * meth_play_audio(PyObject * self, PyObject * args, PyObject * kwargs) {
    const char * keywords[] = {"audio", "loop", NULL};

    int audio;
    int loop = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i|p", (char **)keywords, &audio, &loop)) {
        return NULL;
    }

    audio_play_audio(audio, loop);
    Py_RETURN_NONE;
}

static PyObject * meth_load_qoa(PyObject * self, PyObject * args, PyObject * kwargs) {
    const char * keywords[] = {"data", NULL};

    PyObject * data;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O!", (char **)keywords, &PyBytes_Type, &data)) {
        return NULL;
    }

    qoa_desc qoa;
    short * wave = qoa_decode((unsigned char *)PyBytes_AsString(data), (int)PyBytes_Size(data), &qoa);
    PyObject * res = PyBytes_FromStringAndSize((char *)wave, qoa.channels * qoa.samples * sizeof(short));
    return Py_BuildValue("(iiiN)", qoa.channels, qoa.samples, qoa.samplerate, res);
}

static PyMethodDef module_methods[] = {
    {"load_audio", (PyCFunction)meth_load_audio, METH_VARARGS | METH_KEYWORDS, NULL},
    {"play_audio", (PyCFunction)meth_play_audio, METH_VARARGS | METH_KEYWORDS, NULL},
    {"load_qoa", (PyCFunction)meth_load_qoa, METH_VARARGS | METH_KEYWORDS, NULL},
    {0},
};

static PyModuleDef module_def = {PyModuleDef_HEAD_INIT, "audio", NULL, -1, module_methods};

extern PyObject * PyInit_audio() {
    PyObject * module = PyModule_Create(&module_def);
    return module;
}
