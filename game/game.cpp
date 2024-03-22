#include <Python.h>
#include <structmember.h>

#include <btBulletDynamicsCommon.h>

const double pi = 3.14159265358979323846;

btDefaultCollisionConfiguration * collision_configuration;
btCollisionDispatcher * dispatcher;
btBroadphaseInterface * broadphase;
btSequentialImpulseConstraintSolver * solver;
btDiscreteDynamicsWorld * world;

struct Bone {
    float x, y, z;
    float rx, ry, rz, rw;
    float sx, sy, sz;
    // float r, g, b;
};

const double timestep = 1.0 / 60.0;

btRigidBody * tube;
btRigidBody * boxes[64];

int num_particles;
btRigidBody * particles[256];

btRigidBody * rbody(double mass, btCollisionShape * shape, btVector3 position = {0.0, 0.0, 0.0}, btQuaternion rotation = {0.0, 0.0, 0.0, 1.0}) {
    btVector3 intertia = {0.0, 0.0, 0.0};
    if (mass) {
        shape->calculateLocalInertia(mass, intertia);
    }
    btTransform transform = btTransform(rotation, position);
    btRigidBody * body = new btRigidBody(mass, NULL, shape, intertia);
    body->setActivationState(DISABLE_DEACTIVATION);
    body->setWorldTransform(transform);
    world->addRigidBody(body);
    return body;
}

Bone get_bone(btRigidBody * body) {
    const btTransform & transform = body->getWorldTransform();
    const btVector3 & p = transform.getOrigin();
    const btQuaternion & r = transform.getRotation();
    btBoxShape * shape = (btBoxShape *)body->getCollisionShape();
    const btVector3 s = shape->getHalfExtentsWithMargin() * 2.0;
    return {
        (float)p.x(), (float)p.y(), (float)p.z(),
        (float)r.x(), (float)r.y(), (float)r.z(), (float)r.w(),
        (float)s.x(), (float)s.y(), (float)s.z(),
    };
}

double rng() {
    return (double)(rand() % 1000) / 1000.0;
}

void set_friction(btRigidBody * body, double friction, double rolling_friction, double spinning_friction) {
    body->setFriction(friction);
    body->setRollingFriction(rolling_friction);
    body->setSpinningFriction(spinning_friction);
}

static PyObject * meth_init(PyObject * self, PyObject * args, PyObject * kwargs) {
    collision_configuration = new btDefaultCollisionConfiguration();
    dispatcher = new btCollisionDispatcher(collision_configuration);
    broadphase = new btDbvtBroadphase();
    solver = new btSequentialImpulseConstraintSolver();
    world = new btDiscreteDynamicsWorld(dispatcher, broadphase, solver, collision_configuration);
    world->setGravity({0.0, 0.0, -10.0});
    // world->setGravity({0.0, 0.0, 0.0});

    btCompoundShape * tube_shape = new btCompoundShape();
    for (int i = 0; i < 32; ++i) {
        double angle = pi * 2.0 * i / 32.0 + 1.0 / 64.0;
        btQuaternion rotation = {-sin(angle * 0.5), 0.0, 0.0, cos(angle * 0.5)};
        btVector3 size = {200.0, 1.0, 1.0};
        double radius = 5.0 + size.z() * 0.5 - 0.1;
        btVector3 position = {0.0, sin(angle) * radius, cos(angle) * radius};
        tube_shape->addChildShape(btTransform(rotation, position), new btBoxShape(size * 0.5));
    }

    tube = rbody(0.0, tube_shape, {100.0, 0.0, 0.0});
    tube->setCollisionFlags(tube->getCollisionFlags() | btCollisionObject::CF_KINEMATIC_OBJECT);
    tube->setFriction(1.0);
    tube->setRollingFriction(0.1);
    tube->setSpinningFriction(0.1);
    set_friction(tube, 1.0, 0.1, 0.1);
    for (int i = 0; i < 64; ++i) {
        boxes[i] = rbody(1.0, new btBoxShape({0.5, 0.5, 0.5}), {100.0 + rng() * 50.0 - 25.0, 3.0 + rng(), 1.0 + rng()});
        set_friction(boxes[i], 1.0, 0.1, 0.1);
    }
    Py_RETURN_NONE;
}

double now;

static PyObject * meth_update(PyObject * self, PyObject * args, PyObject * kwargs) {
    now += timestep;
    // tube->setWorldTransform(btTransform({sin(now * 0.4), 0.0, 0.0, cos(now * 0.4)}, {0.0, 0.0, 0.0}));
    tube->setWorldTransform(btTransform({sin(now * 0.6), 0.0, 0.0, cos(now * 0.6)}, {100.0, 0.0, 0.0}));
    for (int i = 0; i < 64; ++i) {
        boxes[i]->applyForce({-7.0, 0.0, 0.0}, {0.0, 0.0, 0.0});
        btTransform t = boxes[i]->getWorldTransform();
        if (t.getOrigin().x() < -10.0) {
            world->removeRigidBody(boxes[i]);
            boxes[i] = rbody(1.0, new btBoxShape({0.5, 0.5, 0.5}), {100.0 + rng() * 50.0 - 25.0, 3.0 + rng(), 1.0 + rng()});
            set_friction(boxes[i], 1.0, 0.1, 0.1);
        }
    }
    for (int i = 0; i < num_particles; ++i) {
        int life = particles[i]->getUserIndex();
        particles[i]->setUserIndex(life - 1);
        if (life <= 0) {
            world->removeRigidBody(particles[i]);
            particles[i] = particles[num_particles - 1];
            --num_particles;
            --i;
        }
    }
    world->stepSimulation(timestep, 0, timestep);
    Py_RETURN_NONE;
}

static PyObject * meth_explode(PyObject * self, PyObject * args, PyObject * kwargs) {
    const char * keywords[] = {"box", NULL};

    int box;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i", (char **)keywords, &box)) {
        return NULL;
    }

    if (box < 0 || box >= 64) {
        Py_RETURN_NONE;
    }

    btTransform parent_transform = boxes[box]->getWorldTransform();
    btVector3 parent_position = parent_transform.getOrigin();

    for (int i = 0; i < 64; ++i) {
        if (i == box) {
            continue;
        }
        btVector3 direction = boxes[i]->getWorldTransform().getOrigin() - parent_position;
        double distance = direction.length();
        if (distance < 15.0) {
            boxes[i]->applyForce(direction / distance / distance * 1000.0, {0.0, 0.0, 0.0});
        }
    }

    for (int i = 0; i < 16; ++i) {
        btVector3 direction = {rng() - 0.5, rng() - 0.5, rng() - 0.5};
        btVector3 position = parent_transform * direction;
        btRigidBody * particle = rbody(0.1, new btBoxShape({0.1, 0.1, 0.1}), position, parent_transform.getRotation());
        particle->setLinearVelocity(boxes[box]->getLinearVelocity());
        particle->applyForce(direction * 100.0, {0.0, 0.0, 0.0});
        particle->setUserIndex(60);
        particles[num_particles++] = particle;
    }

    world->removeRigidBody(boxes[box]);
    boxes[box] = rbody(1.0, new btBoxShape({0.5, 0.5, 0.5}), {100.0 + rng() * 50.0 - 25.0, 3.0 + rng(), 1.0 + rng()});
    set_friction(boxes[box], 1.0, 0.1, 0.1);
    Py_RETURN_NONE;
}

static PyObject * meth_bones(PyObject * self, PyObject * args, PyObject * kwargs) {
    PyObject * res = PyBytes_FromStringAndSize(NULL, (64 + num_particles) * sizeof(Bone));
    Bone * bones = (Bone *)PyBytes_AS_STRING(res);
    for (int i = 0; i < 64; ++i) {
        bones[i] = get_bone(boxes[i]);
    }
    for (int i = 0; i < num_particles; ++i) {
        bones[i + 64] = get_bone(particles[i]);
    }
    return Py_BuildValue("(iN)", 64 + num_particles, res);
}

static PyMethodDef module_methods[] = {
    {"init", (PyCFunction)meth_init, METH_VARARGS | METH_KEYWORDS},
    {"update", (PyCFunction)meth_update, METH_VARARGS | METH_KEYWORDS},
    {"explode", (PyCFunction)meth_explode, METH_VARARGS | METH_KEYWORDS},
    {"bones", (PyCFunction)meth_bones, METH_VARARGS | METH_KEYWORDS},
    {},
};

static PyModuleDef module_def = {PyModuleDef_HEAD_INIT, "game", NULL, -1, module_methods};

extern "C" PyObject * PyInit_game() {
    PyObject * module = PyModule_Create(&module_def);
    return module;
}
