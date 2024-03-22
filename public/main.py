import struct

import js
import pyodide
import zengl

import game
import audio

game.init()

with open('raving-energy.qoa', 'rb') as f:
    music = audio.load_audio(audio.load_qoa(f.read())[3])

with open('breaking-bottle.qoa', 'rb') as f:
    noise = audio.load_audio(audio.load_qoa(f.read())[3])

audio.play_audio(music, loop=True)

ctx = zengl.context()

size = (800, 800)
image = ctx.image((880, 880), 'rgba8unorm')
depth = ctx.image((880, 880), 'depth24plus')
pick = ctx.image((880, 880), 'r32sint')

vertex_buffer = ctx.buffer(open('tube.bin', 'rb').read())
uniform_buffer = ctx.buffer(size=80, uniform=True)

pipeline = ctx.pipeline(
    vertex_shader='''
        #version 300 es
        precision highp float;
        precision highp int;

        layout (std140) uniform Common {
            mat4 camera_matrix;
            float offset;
            float rotate;
        };

        layout (location = 0) in vec3 in_vertex;
        layout (location = 1) in vec3 in_normal;

        out vec3 v_vertex;
        out vec3 v_normal;

        vec3 qtransform(vec4 q, vec3 v) {
            return v + 2.0 * cross(cross(v, q.xyz) - q.w * v, q.xyz);
        }

        void main() {
            float angle = (in_vertex.x * 0.01 + float(gl_InstanceID) - offset) * 1.2;
            vec4 turn = vec4(sin(rotate * 0.5), 0.0, 0.0, cos(rotate * 0.5));
            vec4 rotation = vec4(0.0, 0.0, sin(angle * 0.5), cos(angle * 0.5));
            v_vertex = vec3(0.0, in_vertex.yz);
            v_vertex = qtransform(turn, v_vertex);
            v_vertex = qtransform(rotation, v_vertex) + vec3(sin(angle), 1.0 - cos(angle), 0.0) * 100.0;
            v_normal = in_normal;
            v_normal = qtransform(turn, v_normal);
            v_normal = qtransform(rotation, v_normal);
            gl_Position = camera_matrix * vec4(v_vertex, 1.0);
        }
    ''',
    fragment_shader='''
        #version 300 es
        precision highp float;
        precision highp int;

        in vec3 v_vertex;
        in vec3 v_normal;

        layout (location = 0) out vec4 out_color;

        void main() {
            vec3 camera_position = vec3(0.0, 0.0, 0.0);
            vec3 light_position = vec3(20.0, 0.0, 1.0);
            vec3 light_direction = light_position - v_vertex;

            float ambient = 0.01;
            float facing = 0.01;
            float shininess = 16.0;
            float light_power = 10.0;

            float light_distance = length(light_direction);
            light_distance = light_distance * light_distance;
            light_direction = normalize(light_direction);

            float lambertian = max(dot(light_direction, v_normal), 0.0);
            float specular = 0.0;

            vec3 view_direction = normalize(camera_position - v_vertex);

            if (lambertian > 0.0) {
                vec3 half_direction = normalize(light_direction + view_direction);
                float spec_angle = max(dot(half_direction, v_normal), 0.0);
                specular = pow(spec_angle, shininess);
            }

            float facing_view_dot = max(dot(view_direction, v_normal), 0.0);

            vec3 v_color = vec3(1.0, 1.0, 1.0);
            vec3 light_color = vec3(1.0, 1.0, 1.0);
            vec3 color_linear = v_color * ambient + v_color * facing_view_dot * facing +
                v_color * lambertian * light_color * light_power / light_distance +
                specular * light_color * light_power / light_distance;

            out_color = vec4(pow(color_linear, vec3(1.0 / 2.2)), 1.0);
        }
    ''',
    layout=[
        {
            'name': 'Common',
            'binding': 0,
        },
    ],
    resources=[
        {
            'type': 'uniform_buffer',
            'binding': 0,
            'buffer': uniform_buffer,
        },
    ],
    uniforms={
        'offset': 0.0,
    },
    framebuffer=[image, depth],
    vertex_buffers=zengl.bind(vertex_buffer, '3f 3f', 0, 1),
    vertex_count=vertex_buffer.size // zengl.calcsize('3f 3f'),
    topology='triangles',
    instance_count=2,
)

vertex_buffer_2 = ctx.buffer(open('cube.bin', 'rb').read())
instance_buffer = ctx.buffer(size=16384)

shapes = ctx.pipeline(
    vertex_shader='''
        #version 300 es
        precision highp float;
        precision highp int;

        layout (std140) uniform Common {
            mat4 camera_matrix;
            float offset;
            float rotate;
        };

        layout (location = 0) in vec3 in_vertex;
        layout (location = 1) in vec3 in_normal;

        layout (location = 2) in vec3 in_position;
        layout (location = 3) in vec4 in_rotation;
        layout (location = 4) in vec3 in_scale;

        out vec3 v_vertex;
        out vec3 v_normal;
        flat out int v_id;

        vec3 qtransform(vec4 q, vec3 v) {
            return v + 2.0 * cross(cross(v, q.xyz) - q.w * v, q.xyz);
        }

        void main() {
            v_vertex = in_position + qtransform(in_rotation, in_vertex * in_scale);
            v_normal = qtransform(in_rotation, in_normal);

            float angle = (v_vertex.x * 0.01 - offset * 0.0) * 1.2;
            vec4 rotation = vec4(0.0, 0.0, sin(angle * 0.5), cos(angle * 0.5));
            v_vertex = vec3(0.0, v_vertex.yz);
            v_vertex = qtransform(rotation, v_vertex) + vec3(sin(angle), 1.0 - cos(angle), 0.0) * 100.0;
            v_normal = qtransform(rotation, v_normal);
            v_id = gl_InstanceID + 256;

            gl_Position = camera_matrix * vec4(v_vertex, 1.0);
        }
    ''',
    fragment_shader='''
        #version 300 es
        precision highp float;
        precision highp int;

        in vec3 v_vertex;
        in vec3 v_normal;
        flat in int v_id;

        layout (location = 0) out vec4 out_color;
        layout (location = 1) out int out_id;

        vec3 hsv2rgb(vec3 c) {
            vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
            vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
            return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
        }

        void main() {
            vec3 camera_position = vec3(0.0, 0.0, 0.0);
            vec3 light_position = vec3(20.0, 0.0, 1.0);
            vec3 light_direction = light_position - v_vertex;

            float ambient = 0.01;
            float facing = 0.01;
            float shininess = 16.0;
            float light_power = 10.0;

            float light_distance = length(light_direction);
            light_distance = light_distance * light_distance;
            light_direction = normalize(light_direction);

            float lambertian = max(dot(light_direction, v_normal), 0.0);
            float specular = 0.0;

            vec3 view_direction = normalize(camera_position - v_vertex);

            if (lambertian > 0.0) {
                vec3 half_direction = normalize(light_direction + view_direction);
                float spec_angle = max(dot(half_direction, v_normal), 0.0);
                specular = pow(spec_angle, shininess);
            }

            float facing_view_dot = max(dot(view_direction, v_normal), 0.0);

            vec3 v_color = hsv2rgb(vec3(float(v_id) / 64.0, 1.0, 1.0));
            vec3 light_color = vec3(1.0, 1.0, 1.0);
            vec3 color_linear = v_color * ambient + v_color * facing_view_dot * facing +
                v_color * lambertian * light_color * light_power / light_distance +
                specular * light_color * light_power / light_distance;

            out_color = vec4(pow(color_linear, vec3(1.0 / 2.2)), 1.0);
            out_id = v_id;
        }
    ''',
    layout=[
        {
            'name': 'Common',
            'binding': 0,
        },
    ],
    resources=[
        {
            'type': 'uniform_buffer',
            'binding': 0,
            'buffer': uniform_buffer,
        },
    ],
    framebuffer=[image, pick, depth],
    vertex_buffers=[
        *zengl.bind(vertex_buffer_2, '3f 3f', 0, 1),
        *zengl.bind(instance_buffer, '3f 4f 3f /i', 2, 3, 4),
    ],
    vertex_count=vertex_buffer_2.size // zengl.calcsize('3f 3f'),
    topology='triangles',
    instance_count=2,
)

postprocessing = ctx.pipeline(
    vertex_shader='''
        #version 300 es
        precision highp float;
        precision highp int;

        vec2 positions[3] = vec2[](
            vec2(-1.0, -1.0),
            vec2(3.0, -1.0),
            vec2(-1.0, 3.0)
        );

        void main() {
            gl_Position = vec4(positions[gl_VertexID], 0.0, 1.0);
        }
    ''',
    fragment_shader='''
        #version 300 es
        precision highp float;
        precision highp int;

        uniform sampler2D Texture;
        uniform vec2 position;
        uniform float time;
        uniform int warping;

        layout (location = 0) out vec4 out_color;

        void main() {
            vec2 at = gl_FragCoord.xy + 40.0;
            if (warping > 0) {
                vec2 direction = (position + 40.0) - at;
                float distance = length(direction);
                at += normalize(direction) * sin(time * 10.0) * 50.0 * exp(-4.0 * (time));
                // at += normalize(direction) * sin(distance * 0.1 - time * 10.0) * 100.0 * exp(-4.0 * time) * (1.0 - smoothstep(0.0, 100.0, distance));
            }
            out_color = texelFetch(Texture, ivec2(at), 0);
        }
    ''',
    layout=[
        {
            'name': 'Texture',
            'binding': 0,
        },
    ],
    resources=[
        {
            'type': 'sampler',
            'binding': 0,
            'image': image,
        },
    ],
    uniforms={
        'position': (0, 0),
        'time': 0.0,
        'warping': 0,
    },
    framebuffer=None,
    viewport=(0, 0, *size),
    topology='triangles',
    vertex_count=3,
)

class g:
    explosiont_start = 0.0
    first_timestamp = None

@pyodide.ffi.create_proxy
def render(timestamp=0.0):
    if g.first_timestamp is None:
        g.first_timestamp = timestamp

    mousepress = js.window.mouseClick
    mx, my = js.window.mousePosition
    mx = min(max(int(mx), 0), 800)
    my = min(max(int(my), 0), 800)
    my = size[1] - my - 1
    now = (timestamp - g.first_timestamp) / 1000.0

    ctx.new_frame()
    pick.clear()
    image.clear()
    depth.clear()
    camera = zengl.camera((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    uniform_buffer.write(struct.pack('64s1f1f8x', camera, now * 0.2 % 1.0, now * 1.2))
    # uniform_buffer.write(zengl.camera((0.0, 0.0, 300.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)))
    pipeline.uniforms['offset'][:] = struct.pack('f', now * 0.2 % 1.0)
    pipeline.render()
    game.update()
    count, bones = game.bones()
    instance_buffer.write(bones)
    shapes.instance_count = count
    shapes.render()
    if mousepress:
        postprocessing.uniforms['position'][:] = struct.pack('2f', mx, my)
    postprocessing.uniforms['time'][:] = struct.pack('f', now - g.explosiont_start)
    postprocessing.uniforms['warping'][:] = struct.pack('i', now - g.explosiont_start < 1.0)
    postprocessing.render()
    # image.blit()
    if mousepress:
        picked = pick.read((1, 1), offset=(mx + 40, my + 40))
        picked = struct.unpack('i', picked)[0]
        if picked:
            audio.play_audio(noise)
            game.explode(picked & 0xff)
            g.explosiont_start = now
    ctx.end_frame()

    js.window.mouseClick = False
    js.requestAnimationFrame(render)

js.window.loadingComplete()
render()
