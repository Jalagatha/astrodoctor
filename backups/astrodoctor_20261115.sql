--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.wellbeing_wellbeingcheckin DROP CONSTRAINT IF EXISTS wellbeing_wellbeingcheckin_user_id_f1d83487_fk_auth_user_id;
ALTER TABLE IF EXISTS ONLY public.wellbeing_vrsession DROP CONSTRAINT IF EXISTS wellbeing_vrsession_user_id_90abcd05_fk_auth_user_id;
ALTER TABLE IF EXISTS ONLY public.wellbeing_vrsession DROP CONSTRAINT IF EXISTS wellbeing_vrsession_checkin_id_8e095db2_fk_wellbeing;
ALTER TABLE IF EXISTS ONLY public.wellbeing_trainingjob DROP CONSTRAINT IF EXISTS wellbeing_trainingjob_created_by_id_58fb1eb4_fk_auth_user_id;
ALTER TABLE IF EXISTS ONLY public.health_userprofile DROP CONSTRAINT IF EXISTS health_userprofile_user_id_fb3a9d38_fk_auth_user_id;
ALTER TABLE IF EXISTS ONLY public.django_admin_log DROP CONSTRAINT IF EXISTS django_admin_log_user_id_c564eba6_fk_auth_user_id;
ALTER TABLE IF EXISTS ONLY public.django_admin_log DROP CONSTRAINT IF EXISTS django_admin_log_content_type_id_c4bce8eb_fk_django_co;
ALTER TABLE IF EXISTS ONLY public.auth_user_user_permissions DROP CONSTRAINT IF EXISTS auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id;
ALTER TABLE IF EXISTS ONLY public.auth_user_user_permissions DROP CONSTRAINT IF EXISTS auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm;
ALTER TABLE IF EXISTS ONLY public.auth_user_groups DROP CONSTRAINT IF EXISTS auth_user_groups_user_id_6a12ed8b_fk_auth_user_id;
ALTER TABLE IF EXISTS ONLY public.auth_user_groups DROP CONSTRAINT IF EXISTS auth_user_groups_group_id_97559544_fk_auth_group_id;
ALTER TABLE IF EXISTS ONLY public.auth_permission DROP CONSTRAINT IF EXISTS auth_permission_content_type_id_2f476e4b_fk_django_co;
ALTER TABLE IF EXISTS ONLY public.auth_group_permissions DROP CONSTRAINT IF EXISTS auth_group_permissions_group_id_b120cbf9_fk_auth_group_id;
ALTER TABLE IF EXISTS ONLY public.auth_group_permissions DROP CONSTRAINT IF EXISTS auth_group_permissio_permission_id_84c5c92e_fk_auth_perm;
DROP INDEX IF EXISTS public.wellbeing_wellbeingcheckin_user_id_f1d83487;
DROP INDEX IF EXISTS public.wellbeing_vrsession_user_id_90abcd05;
DROP INDEX IF EXISTS public.wellbeing_trainingjob_created_by_id_58fb1eb4;
DROP INDEX IF EXISTS public.django_session_session_key_c0390e0f_like;
DROP INDEX IF EXISTS public.django_session_expire_date_a5c62663;
DROP INDEX IF EXISTS public.django_admin_log_user_id_c564eba6;
DROP INDEX IF EXISTS public.django_admin_log_content_type_id_c4bce8eb;
DROP INDEX IF EXISTS public.auth_user_username_6821ab7c_like;
DROP INDEX IF EXISTS public.auth_user_user_permissions_user_id_a95ead1b;
DROP INDEX IF EXISTS public.auth_user_user_permissions_permission_id_1fbb5f2c;
DROP INDEX IF EXISTS public.auth_user_groups_user_id_6a12ed8b;
DROP INDEX IF EXISTS public.auth_user_groups_group_id_97559544;
DROP INDEX IF EXISTS public.auth_permission_content_type_id_2f476e4b;
DROP INDEX IF EXISTS public.auth_group_permissions_permission_id_84c5c92e;
DROP INDEX IF EXISTS public.auth_group_permissions_group_id_b120cbf9;
DROP INDEX IF EXISTS public.auth_group_name_a6ea08ec_like;
ALTER TABLE IF EXISTS ONLY public.wellbeing_wellbeingcheckin DROP CONSTRAINT IF EXISTS wellbeing_wellbeingcheckin_pkey;
ALTER TABLE IF EXISTS ONLY public.wellbeing_vrsession DROP CONSTRAINT IF EXISTS wellbeing_vrsession_pkey;
ALTER TABLE IF EXISTS ONLY public.wellbeing_vrsession DROP CONSTRAINT IF EXISTS wellbeing_vrsession_checkin_id_key;
ALTER TABLE IF EXISTS ONLY public.wellbeing_trainingjob DROP CONSTRAINT IF EXISTS wellbeing_trainingjob_pkey;
ALTER TABLE IF EXISTS ONLY public.health_userprofile DROP CONSTRAINT IF EXISTS health_userprofile_user_id_key;
ALTER TABLE IF EXISTS ONLY public.health_userprofile DROP CONSTRAINT IF EXISTS health_userprofile_pkey;
ALTER TABLE IF EXISTS ONLY public.health_developer DROP CONSTRAINT IF EXISTS health_developer_slot_key;
ALTER TABLE IF EXISTS ONLY public.health_developer DROP CONSTRAINT IF EXISTS health_developer_pkey;
ALTER TABLE IF EXISTS ONLY public.health_crewmember DROP CONSTRAINT IF EXISTS health_crewmember_pkey;
ALTER TABLE IF EXISTS ONLY public.django_session DROP CONSTRAINT IF EXISTS django_session_pkey;
ALTER TABLE IF EXISTS ONLY public.django_migrations DROP CONSTRAINT IF EXISTS django_migrations_pkey;
ALTER TABLE IF EXISTS ONLY public.django_content_type DROP CONSTRAINT IF EXISTS django_content_type_pkey;
ALTER TABLE IF EXISTS ONLY public.django_content_type DROP CONSTRAINT IF EXISTS django_content_type_app_label_model_76bd3d3b_uniq;
ALTER TABLE IF EXISTS ONLY public.django_admin_log DROP CONSTRAINT IF EXISTS django_admin_log_pkey;
ALTER TABLE IF EXISTS ONLY public.auth_user DROP CONSTRAINT IF EXISTS auth_user_username_key;
ALTER TABLE IF EXISTS ONLY public.auth_user_user_permissions DROP CONSTRAINT IF EXISTS auth_user_user_permissions_user_id_permission_id_14a6b632_uniq;
ALTER TABLE IF EXISTS ONLY public.auth_user_user_permissions DROP CONSTRAINT IF EXISTS auth_user_user_permissions_pkey;
ALTER TABLE IF EXISTS ONLY public.auth_user DROP CONSTRAINT IF EXISTS auth_user_pkey;
ALTER TABLE IF EXISTS ONLY public.auth_user_groups DROP CONSTRAINT IF EXISTS auth_user_groups_user_id_group_id_94350c0c_uniq;
ALTER TABLE IF EXISTS ONLY public.auth_user_groups DROP CONSTRAINT IF EXISTS auth_user_groups_pkey;
ALTER TABLE IF EXISTS ONLY public.auth_permission DROP CONSTRAINT IF EXISTS auth_permission_pkey;
ALTER TABLE IF EXISTS ONLY public.auth_permission DROP CONSTRAINT IF EXISTS auth_permission_content_type_id_codename_01ab375a_uniq;
ALTER TABLE IF EXISTS ONLY public.auth_group DROP CONSTRAINT IF EXISTS auth_group_pkey;
ALTER TABLE IF EXISTS ONLY public.auth_group_permissions DROP CONSTRAINT IF EXISTS auth_group_permissions_pkey;
ALTER TABLE IF EXISTS ONLY public.auth_group_permissions DROP CONSTRAINT IF EXISTS auth_group_permissions_group_id_permission_id_0cd325b0_uniq;
ALTER TABLE IF EXISTS ONLY public.auth_group DROP CONSTRAINT IF EXISTS auth_group_name_key;
DROP TABLE IF EXISTS public.wellbeing_wellbeingcheckin;
DROP TABLE IF EXISTS public.wellbeing_vrsession;
DROP TABLE IF EXISTS public.wellbeing_trainingjob;
DROP TABLE IF EXISTS public.health_userprofile;
DROP TABLE IF EXISTS public.health_developer;
DROP TABLE IF EXISTS public.health_crewmember;
DROP TABLE IF EXISTS public.django_session;
DROP TABLE IF EXISTS public.django_migrations;
DROP TABLE IF EXISTS public.django_content_type;
DROP TABLE IF EXISTS public.django_admin_log;
DROP TABLE IF EXISTS public.auth_user_user_permissions;
DROP TABLE IF EXISTS public.auth_user_groups;
DROP TABLE IF EXISTS public.auth_user;
DROP TABLE IF EXISTS public.auth_permission;
DROP TABLE IF EXISTS public.auth_group_permissions;
DROP TABLE IF EXISTS public.auth_group;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


--
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_user_groups (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_user ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_user_user_permissions (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_admin_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


--
-- Name: health_crewmember; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.health_crewmember (
    id bigint NOT NULL,
    full_name character varying(120) NOT NULL,
    call_sign character varying(40) NOT NULL,
    role character varying(100) NOT NULL,
    agency character varying(100) NOT NULL,
    nationality character varying(80) NOT NULL,
    mission character varying(120) NOT NULL,
    mission_start date,
    date_of_birth date,
    email character varying(254) NOT NULL,
    biography text NOT NULL,
    photo character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: health_crewmember_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.health_crewmember ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.health_crewmember_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: health_developer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.health_developer (
    id bigint NOT NULL,
    slot smallint NOT NULL,
    full_name character varying(120) NOT NULL,
    role character varying(100) NOT NULL,
    biography text NOT NULL,
    email character varying(254) NOT NULL,
    github character varying(200) NOT NULL,
    website character varying(200) NOT NULL,
    photo character varying(100) NOT NULL,
    CONSTRAINT developer_slot_1_to_5 CHECK (((slot >= 1) AND (slot <= 5))),
    CONSTRAINT health_developer_slot_check CHECK ((slot >= 0))
);


--
-- Name: health_developer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.health_developer ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.health_developer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: health_userprofile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.health_userprofile (
    id bigint NOT NULL,
    display_name character varying(120) NOT NULL,
    job_title character varying(100) NOT NULL,
    biography text NOT NULL,
    photo character varying(100) NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: health_userprofile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.health_userprofile ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.health_userprofile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: wellbeing_trainingjob; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wellbeing_trainingjob (
    id bigint NOT NULL,
    kind character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    params jsonb NOT NULL,
    result jsonb NOT NULL,
    error text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    created_by_id integer
);


--
-- Name: wellbeing_trainingjob_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.wellbeing_trainingjob ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.wellbeing_trainingjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: wellbeing_vrsession; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wellbeing_vrsession (
    id bigint NOT NULL,
    status character varying(20) NOT NULL,
    model_version character varying(60) NOT NULL,
    recommended_scene character varying(20) NOT NULL,
    recommended_minutes smallint NOT NULL,
    exploring boolean NOT NULL,
    ranking jsonb NOT NULL,
    reasons jsonb NOT NULL,
    scene character varying(20) NOT NULL,
    predicted_gain double precision,
    planned_minutes smallint,
    started_at timestamp with time zone,
    ended_at timestamp with time zone,
    minutes_completed double precision,
    mood_after smallint,
    energy_after smallint,
    stress_after smallint,
    enjoyment smallint,
    rechecked_at timestamp with time zone,
    user_id integer NOT NULL,
    checkin_id bigint NOT NULL,
    CONSTRAINT wellbeing_vrsession_energy_after_check CHECK ((energy_after >= 0)),
    CONSTRAINT wellbeing_vrsession_enjoyment_check CHECK ((enjoyment >= 0)),
    CONSTRAINT wellbeing_vrsession_mood_after_check CHECK ((mood_after >= 0)),
    CONSTRAINT wellbeing_vrsession_planned_minutes_check CHECK ((planned_minutes >= 0)),
    CONSTRAINT wellbeing_vrsession_recommended_minutes_check CHECK ((recommended_minutes >= 0)),
    CONSTRAINT wellbeing_vrsession_stress_after_check CHECK ((stress_after >= 0))
);


--
-- Name: wellbeing_vrsession_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.wellbeing_vrsession ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.wellbeing_vrsession_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: wellbeing_wellbeingcheckin; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wellbeing_wellbeingcheckin (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    mission_day integer NOT NULL,
    mission_phase character varying(20) NOT NULL,
    time_block character varying(20) NOT NULL,
    mood smallint NOT NULL,
    energy smallint NOT NULL,
    stress smallint NOT NULL,
    homesickness smallint NOT NULL,
    sleep_hours double precision NOT NULL,
    user_id integer NOT NULL,
    CONSTRAINT wellbeing_wellbeingcheckin_energy_check CHECK ((energy >= 0)),
    CONSTRAINT wellbeing_wellbeingcheckin_homesickness_check CHECK ((homesickness >= 0)),
    CONSTRAINT wellbeing_wellbeingcheckin_mission_day_check CHECK ((mission_day >= 0)),
    CONSTRAINT wellbeing_wellbeingcheckin_mood_check CHECK ((mood >= 0)),
    CONSTRAINT wellbeing_wellbeingcheckin_stress_check CHECK ((stress >= 0))
);


--
-- Name: wellbeing_wellbeingcheckin_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.wellbeing_wellbeingcheckin ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.wellbeing_wellbeingcheckin_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add permission	3	add_permission
6	Can change permission	3	change_permission
7	Can delete permission	3	delete_permission
8	Can view permission	3	view_permission
9	Can add group	2	add_group
10	Can change group	2	change_group
11	Can delete group	2	delete_group
12	Can view group	2	view_group
13	Can add user	4	add_user
14	Can change user	4	change_user
15	Can delete user	4	delete_user
16	Can view user	4	view_user
17	Can add content type	5	add_contenttype
18	Can change content type	5	change_contenttype
19	Can delete content type	5	delete_contenttype
20	Can view content type	5	view_contenttype
21	Can add session	6	add_session
22	Can change session	6	change_session
23	Can delete session	6	delete_session
24	Can view session	6	view_session
25	Can add check in	7	add_checkin
26	Can change check in	7	change_checkin
27	Can delete check in	7	delete_checkin
28	Can view check in	7	view_checkin
29	Can add daily record	9	add_dailyrecord
30	Can change daily record	9	change_dailyrecord
31	Can delete daily record	9	delete_dailyrecord
32	Can view daily record	9	view_dailyrecord
33	Can add dataset lock	11	add_datasetlock
34	Can change dataset lock	11	change_datasetlock
35	Can delete dataset lock	11	delete_datasetlock
36	Can view dataset lock	11	view_datasetlock
37	Can add crew member	8	add_crewmember
38	Can change crew member	8	change_crewmember
39	Can delete crew member	8	delete_crewmember
40	Can view crew member	8	view_crewmember
41	Can add developer	12	add_developer
42	Can change developer	12	change_developer
43	Can delete developer	12	delete_developer
44	Can view developer	12	view_developer
45	Can add user profile	13	add_userprofile
46	Can change user profile	13	change_userprofile
47	Can delete user profile	13	delete_userprofile
48	Can view user profile	13	view_userprofile
49	Can add dataset calibration	10	add_datasetcalibration
50	Can change dataset calibration	10	change_datasetcalibration
51	Can delete dataset calibration	10	delete_datasetcalibration
52	Can view dataset calibration	10	view_datasetcalibration
53	Can add astronaut	16	add_astronaut
54	Can change astronaut	16	change_astronaut
55	Can delete astronaut	16	delete_astronaut
56	Can view astronaut	16	view_astronaut
57	Can add audit entry	17	add_auditentry
58	Can change audit entry	17	change_auditentry
59	Can delete audit entry	17	delete_auditentry
60	Can view audit entry	17	view_auditentry
61	Can add exposure	19	add_exposure
62	Can change exposure	19	change_exposure
63	Can delete exposure	19	delete_exposure
64	Can view exposure	19	view_exposure
65	Can add import report	26	add_importreport
66	Can change import report	26	change_importreport
67	Can delete import report	26	delete_importreport
68	Can view import report	26	view_importreport
69	Can add rule version	30	add_ruleversion
70	Can change rule version	30	change_ruleversion
71	Can delete rule version	30	delete_ruleversion
72	Can view rule version	30	view_ruleversion
73	Can add demo account	18	add_demoaccount
74	Can change demo account	18	change_demoaccount
75	Can delete demo account	18	delete_demoaccount
76	Can view demo account	18	view_demoaccount
77	Can add finding	20	add_finding
78	Can change finding	20	change_finding
79	Can delete finding	20	delete_finding
80	Can view finding	20	view_finding
81	Can add alert action	14	add_alertaction
82	Can change alert action	14	change_alertaction
83	Can delete alert action	14	delete_alertaction
84	Can view alert action	14	view_alertaction
85	Can add mission check in	28	add_missioncheckin
86	Can change mission check in	28	change_missioncheckin
87	Can delete mission check in	28	delete_missioncheckin
88	Can view mission check in	28	view_missioncheckin
89	Can add assessment	15	add_assessment
90	Can change assessment	15	change_assessment
91	Can delete assessment	15	delete_assessment
92	Can view assessment	15	view_assessment
93	Can add mission access	27	add_missionaccess
94	Can change mission access	27	change_missionaccess
95	Can delete mission access	27	delete_missionaccess
96	Can view mission access	27	view_missionaccess
97	Can add observation	29	add_observation
98	Can change observation	29	change_observation
99	Can delete observation	29	delete_observation
100	Can view observation	29	view_observation
101	Can add ground link state	23	add_groundlinkstate
102	Can change ground link state	23	change_groundlinkstate
103	Can delete ground link state	23	delete_groundlinkstate
104	Can view ground link state	23	view_groundlinkstate
105	Can add triage protocol	32	add_triageprotocol
106	Can change triage protocol	32	change_triageprotocol
107	Can delete triage protocol	32	delete_triageprotocol
108	Can view triage protocol	32	view_triageprotocol
109	Can add finding override	21	add_findingoverride
110	Can change finding override	21	change_findingoverride
111	Can delete finding override	21	delete_findingoverride
112	Can view finding override	21	view_findingoverride
113	Can add ground packet	24	add_groundpacket
114	Can change ground packet	24	change_groundpacket
115	Can delete ground packet	24	delete_groundpacket
116	Can view ground packet	24	view_groundpacket
117	Can add ground guidance	22	add_groundguidance
118	Can change ground guidance	22	change_groundguidance
119	Can delete ground guidance	22	delete_groundguidance
120	Can view ground guidance	22	view_groundguidance
121	Can add triage session	33	add_triagesession
122	Can change triage session	33	change_triagesession
123	Can delete triage session	33	delete_triagesession
124	Can view triage session	33	view_triagesession
125	Can add guidance read	25	add_guidanceread
126	Can change guidance read	25	change_guidanceread
127	Can delete guidance read	25	delete_guidanceread
128	Can view guidance read	25	view_guidanceread
129	Can add triage answer	31	add_triageanswer
130	Can change triage answer	31	change_triageanswer
131	Can delete triage answer	31	delete_triageanswer
132	Can view triage answer	31	view_triageanswer
133	Can add wellbeing check in	35	add_wellbeingcheckin
134	Can change wellbeing check in	35	change_wellbeingcheckin
135	Can delete wellbeing check in	35	delete_wellbeingcheckin
136	Can view wellbeing check in	35	view_wellbeingcheckin
137	Can add vr session	34	add_vrsession
138	Can change vr session	34	change_vrsession
139	Can delete vr session	34	delete_vrsession
140	Can view vr session	34	view_vrsession
141	Can add training job	36	add_trainingjob
142	Can change training job	36	change_trainingjob
143	Can delete training job	36	delete_trainingjob
144	Can view training job	36	view_trainingjob
\.


--
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) FROM stdin;
1	pbkdf2_sha256$1500000$60bdF4m9JUqPy1qVZa3hxt$Uuv7CIwVgEpCmUWefIBNtRK5fc8kmSMn9q3Jlo38ADw=	2026-11-15 19:30:18.427728+03	t	engdave				t	t	2026-11-15 06:49:37.211414+03
\.


--
-- Data for Name: auth_user_groups; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auth_user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- Data for Name: auth_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auth_user_user_permissions (id, user_id, permission_id) FROM stdin;
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
\.


--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	admin	logentry
2	auth	group
3	auth	permission
4	auth	user
5	contenttypes	contenttype
6	sessions	session
7	health	checkin
8	health	crewmember
9	health	dailyrecord
10	health	datasetcalibration
11	health	datasetlock
12	health	developer
13	health	userprofile
14	meridian	alertaction
15	meridian	assessment
16	meridian	astronaut
17	meridian	auditentry
18	meridian	demoaccount
19	meridian	exposure
20	meridian	finding
21	meridian	findingoverride
22	meridian	groundguidance
23	meridian	groundlinkstate
24	meridian	groundpacket
25	meridian	guidanceread
26	meridian	importreport
27	meridian	missionaccess
28	meridian	missioncheckin
29	meridian	observation
30	meridian	ruleversion
31	meridian	triageanswer
32	meridian	triageprotocol
33	meridian	triagesession
34	wellbeing	vrsession
35	wellbeing	wellbeingcheckin
36	wellbeing	trainingjob
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2026-11-15 06:49:10.436194+03
2	auth	0001_initial	2026-11-15 06:49:10.549344+03
3	admin	0001_initial	2026-11-15 06:49:10.585083+03
4	admin	0002_logentry_remove_auto_add	2026-11-15 06:49:10.594219+03
5	admin	0003_logentry_add_action_flag_choices	2026-11-15 06:49:10.603192+03
6	contenttypes	0002_remove_content_type_name	2026-11-15 06:49:10.622676+03
7	auth	0002_alter_permission_name_max_length	2026-11-15 06:49:10.63191+03
8	auth	0003_alter_user_email_max_length	2026-11-15 06:49:10.64185+03
9	auth	0004_alter_user_username_opts	2026-11-15 06:49:10.649698+03
10	auth	0005_alter_user_last_login_null	2026-11-15 06:49:10.659113+03
11	auth	0006_require_contenttypes_0002	2026-11-15 06:49:10.66051+03
12	auth	0007_alter_validators_add_error_messages	2026-11-15 06:49:10.669696+03
13	auth	0008_alter_user_username_max_length	2026-11-15 06:49:10.684548+03
14	auth	0009_alter_user_last_name_max_length	2026-11-15 06:49:10.705411+03
15	auth	0010_alter_group_name_max_length	2026-11-15 06:49:10.717363+03
16	auth	0011_update_proxy_permissions	2026-11-15 06:49:10.727987+03
17	auth	0012_alter_user_first_name_max_length	2026-11-15 06:49:10.742227+03
18	health	0001_initial	2026-11-15 06:49:10.78783+03
19	health	0002_crewmember	2026-11-15 06:49:10.811747+03
20	health	0003_developer	2026-11-15 06:49:10.835789+03
21	health	0004_userprofile	2026-11-15 06:49:10.883339+03
22	health	0005_datasetcalibration	2026-11-15 06:49:10.898248+03
23	meridian	0001_initial	2026-11-15 06:49:11.420027+03
24	meridian	0002_groundlinkstate_triageprotocol_findingoverride_and_more	2026-11-15 06:49:11.916896+03
25	sessions	0001_initial	2026-11-15 06:49:11.955391+03
26	wellbeing	0001_initial	2026-11-15 18:37:26.115914+03
27	wellbeing	0002_trainingjob	2026-11-15 18:52:59.118563+03
28	health	0006_remove_health_dashboard	2026-11-15 19:28:14.609833+03
\.


--
-- Data for Name: health_crewmember; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.health_crewmember (id, full_name, call_sign, role, agency, nationality, mission, mission_start, date_of_birth, email, biography, photo, status, updated_at) FROM stdin;
\.


--
-- Data for Name: health_developer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.health_developer (id, slot, full_name, role, biography, email, github, website, photo) FROM stdin;
1	1	Mugisha Ivan Jalagatha	Developer		jalagatha@gmail.com	https://github.com/jalagatha		crew/0819577cd2fb45ceadae9559164f71df.jpg
2	2	David Hope Kinyonyi	Developer		kinyonyidavid@gmail.com	https://github.com/kinyonyi		crew/2dc3ecacac73442c906acab6ba49e3a3.jpg
3	3	Walubo Nathan	Human Explorer		nathanwalubo@gmail.com	https://github.com/walubonathan		crew/c4141a4290f04182ba743b1808231325.jpg
4	4	Kaliisa Daniel	UI/Ux Developer		kaliisadanniel1@gmail.com	https://github.com/digne0		crew/5357e04001e7440ea52b7d10a5c65cde.jpg
5	5	Okoth Bruno	Team Lead		brunoike42@gmail.com	https://github.com/brunoike		crew/0d077933beb44794ba1ad9b03f4555f1.jpg
\.


--
-- Data for Name: health_userprofile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.health_userprofile (id, display_name, job_title, biography, photo, user_id) FROM stdin;
\.


--
-- Data for Name: wellbeing_trainingjob; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.wellbeing_trainingjob (id, kind, status, params, result, error, created_at, started_at, finished_at, created_by_id) FROM stdin;
\.


--
-- Data for Name: wellbeing_vrsession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.wellbeing_vrsession (id, status, model_version, recommended_scene, recommended_minutes, exploring, ranking, reasons, scene, predicted_gain, planned_minutes, started_at, ended_at, minutes_completed, mood_after, energy_after, stress_after, enjoyment, rechecked_at, user_id, checkin_id) FROM stdin;
2	rechecked	scene-rec-20261115-155019	calm	10	f	[{"key": "calm", "score": 0.392, "blocked": null, "sessions": 1, "predicted": 0.163, "adjustment": 0.358, "uncertainty": 0.318}, {"key": "family", "score": 0.213, "blocked": null, "sessions": 0, "predicted": 0.468, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "learning", "score": 0.167, "blocked": null, "sessions": 0, "predicted": 0.321, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "active", "score": 0.159, "blocked": null, "sessions": 0, "predicted": 0.176, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "nature", "score": -0.294, "blocked": null, "sessions": 0, "predicted": 0.051, "adjustment": 0.0, "uncertainty": 0.35}]	["Your 6 h sleep lowers the predicted benefit by 0.2.", "Your work-day break lowers the predicted benefit by 0.1.", "From your 1 past re-check of this scene, your personal adjustment is +0.4."]	calm	0.16268215719514795	10	2026-11-15 19:31:49.79679+03	2026-11-15 19:32:17.37236+03	0.5	3	4	4	5	2026-11-15 19:32:42.184106+03	1	2
1	rechecked	scene-rec-20261115-153609	calm	15	f	[{"key": "calm", "score": 0.554, "blocked": null, "sessions": 0, "predicted": 0.451, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "active", "score": 0.372, "blocked": null, "sessions": 0, "predicted": 0.085, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "family", "score": 0.034, "blocked": null, "sessions": 0, "predicted": 0.31, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "nature", "score": -0.037, "blocked": null, "sessions": 0, "predicted": 0.232, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "learning", "score": -0.295, "blocked": "Learning is paused after very short sleep (under 4.5 h).", "sessions": 0, "predicted": -0.068, "adjustment": 0.0, "uncertainty": 0.35}]	["Your stress 4/5 raises the predicted benefit by 0.2."]	calm	0.45139046642162123	15	2026-11-15 18:43:29.804318+03	2026-11-15 18:43:45.416799+03	0.3	5	3	3	4	2026-11-15 19:14:45.076486+03	1	1
3	rechecked	scene-rec-20261115-155019	calm	15	f	[{"key": "calm", "score": 1.047, "blocked": null, "sessions": 2, "predicted": 0.736, "adjustment": 0.206, "uncertainty": 0.293}, {"key": "family", "score": 0.547, "blocked": null, "sessions": 0, "predicted": 0.597, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "nature", "score": 0.543, "blocked": null, "sessions": 0, "predicted": 0.542, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "active", "score": -0.283, "blocked": null, "sessions": 0, "predicted": 0.257, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "learning", "score": -0.302, "blocked": "Learning is paused after very short sleep (under 4.5 h).", "sessions": 0, "predicted": -0.156, "adjustment": 0.0, "uncertainty": 0.35}]	["Your stress 4/5 raises the predicted benefit by 0.3.", "Your mood 2/5 raises the predicted benefit by 0.2.", "Your 3 h sleep lowers the predicted benefit by 0.1.", "From your 2 past re-checks of this scene, your personal adjustment is +0.2."]	calm	0.7355767409467038	15	2026-11-15 19:47:20.703713+03	2026-11-15 19:48:35.619604+03	1.2	3	3	3	4	2026-11-15 19:48:50.429856+03	1	3
4	rechecked	scene-rec-20261115-155019	family	10	t	[{"key": "family", "score": 1.335, "blocked": null, "sessions": 0, "predicted": 0.836, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "nature", "score": 1.101, "blocked": null, "sessions": 0, "predicted": 0.599, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "active", "score": 0.826, "blocked": null, "sessions": 0, "predicted": 0.621, "adjustment": 0.0, "uncertainty": 0.35}, {"key": "calm", "score": 0.56, "blocked": null, "sessions": 3, "predicted": 0.679, "adjustment": 0.278, "uncertainty": 0.274}, {"key": "learning", "score": 0.92, "blocked": "Learning is paused after very short sleep (under 4.5 h).", "sessions": 0, "predicted": 0.611, "adjustment": 0.0, "uncertainty": 0.35}]	["Your missing home 4/5 raises the predicted benefit by 0.2.", "Your mood 1/5 raises the predicted benefit by 0.2.", "Your 3 h sleep raises the predicted benefit by 0.1.", "Exploring: Garden at dusk has a slightly higher expected benefit, but the engine is still learning how this scene works for you."]	family	0.8357976895978492	10	2026-11-15 20:07:02.484228+03	2026-11-15 20:07:55.10347+03	0.9	3	4	1	3	2026-11-15 20:08:07.842409+03	1	4
\.


--
-- Data for Name: wellbeing_wellbeingcheckin; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.wellbeing_wellbeingcheckin (id, created_at, mission_day, mission_phase, time_block, mood, energy, stress, homesickness, sleep_hours, user_id) FROM stdin;
1	2026-11-15 18:43:17.256087+03	15	adaptation	evening	3	2	4	3	4	1
2	2026-11-15 19:31:24.697067+03	16	adaptation	work	3	4	3	5	6	1
3	2026-11-15 19:47:02.367885+03	17	adaptation	evening	2	2	4	5	3	1
4	2026-11-15 20:06:57.868691+03	17	adaptation	work	1	3	2	4	3	1
\.


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 144, true);


--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auth_user_groups_id_seq', 1, false);


--
-- Name: auth_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auth_user_id_seq', 1, true);


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auth_user_user_permissions_id_seq', 1, false);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 1, false);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 36, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 28, true);


--
-- Name: health_crewmember_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.health_crewmember_id_seq', 1, false);


--
-- Name: health_developer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.health_developer_id_seq', 5, true);


--
-- Name: health_userprofile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.health_userprofile_id_seq', 1, false);


--
-- Name: wellbeing_trainingjob_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.wellbeing_trainingjob_id_seq', 1, false);


--
-- Name: wellbeing_vrsession_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.wellbeing_vrsession_id_seq', 4, true);


--
-- Name: wellbeing_wellbeingcheckin_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.wellbeing_wellbeingcheckin_id_seq', 4, true);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);


--
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: health_crewmember health_crewmember_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_crewmember
    ADD CONSTRAINT health_crewmember_pkey PRIMARY KEY (id);


--
-- Name: health_developer health_developer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_developer
    ADD CONSTRAINT health_developer_pkey PRIMARY KEY (id);


--
-- Name: health_developer health_developer_slot_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_developer
    ADD CONSTRAINT health_developer_slot_key UNIQUE (slot);


--
-- Name: health_userprofile health_userprofile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_userprofile
    ADD CONSTRAINT health_userprofile_pkey PRIMARY KEY (id);


--
-- Name: health_userprofile health_userprofile_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_userprofile
    ADD CONSTRAINT health_userprofile_user_id_key UNIQUE (user_id);


--
-- Name: wellbeing_trainingjob wellbeing_trainingjob_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellbeing_trainingjob
    ADD CONSTRAINT wellbeing_trainingjob_pkey PRIMARY KEY (id);


--
-- Name: wellbeing_vrsession wellbeing_vrsession_checkin_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellbeing_vrsession
    ADD CONSTRAINT wellbeing_vrsession_checkin_id_key UNIQUE (checkin_id);


--
-- Name: wellbeing_vrsession wellbeing_vrsession_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellbeing_vrsession
    ADD CONSTRAINT wellbeing_vrsession_pkey PRIMARY KEY (id);


--
-- Name: wellbeing_wellbeingcheckin wellbeing_wellbeingcheckin_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellbeing_wellbeingcheckin
    ADD CONSTRAINT wellbeing_wellbeingcheckin_pkey PRIMARY KEY (id);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);


--
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);


--
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);


--
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);


--
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: wellbeing_trainingjob_created_by_id_58fb1eb4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX wellbeing_trainingjob_created_by_id_58fb1eb4 ON public.wellbeing_trainingjob USING btree (created_by_id);


--
-- Name: wellbeing_vrsession_user_id_90abcd05; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX wellbeing_vrsession_user_id_90abcd05 ON public.wellbeing_vrsession USING btree (user_id);


--
-- Name: wellbeing_wellbeingcheckin_user_id_f1d83487; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX wellbeing_wellbeingcheckin_user_id_f1d83487 ON public.wellbeing_wellbeingcheckin USING btree (user_id);


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: health_userprofile health_userprofile_user_id_fb3a9d38_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_userprofile
    ADD CONSTRAINT health_userprofile_user_id_fb3a9d38_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: wellbeing_trainingjob wellbeing_trainingjob_created_by_id_58fb1eb4_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellbeing_trainingjob
    ADD CONSTRAINT wellbeing_trainingjob_created_by_id_58fb1eb4_fk_auth_user_id FOREIGN KEY (created_by_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: wellbeing_vrsession wellbeing_vrsession_checkin_id_8e095db2_fk_wellbeing; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellbeing_vrsession
    ADD CONSTRAINT wellbeing_vrsession_checkin_id_8e095db2_fk_wellbeing FOREIGN KEY (checkin_id) REFERENCES public.wellbeing_wellbeingcheckin(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: wellbeing_vrsession wellbeing_vrsession_user_id_90abcd05_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellbeing_vrsession
    ADD CONSTRAINT wellbeing_vrsession_user_id_90abcd05_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: wellbeing_wellbeingcheckin wellbeing_wellbeingcheckin_user_id_f1d83487_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wellbeing_wellbeingcheckin
    ADD CONSTRAINT wellbeing_wellbeingcheckin_user_id_f1d83487_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--

