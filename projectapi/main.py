from typing import List, Optional
from fastapi import FastAPI, HTTPException, status, Cookie
import db
import schema
from utils import user


# Init db
db.Base.metadata.create_all(bind=db.engine)


app = FastAPI(
    docs_url='/projectapi/docs',
    openapi_url='/projectapi/openapi.json',
)


@app.get('/projectapi/')
async def index():
    return {'message': 'Hello, projectapi!'}


# CRUD Project

@app.get(
    '/projectapi/project/{id:int}',
    description='Get project',
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            'model': schema.Project,
            'description': 'Successful Response',
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'Project not found',
        },
    },
)
async def get_project(id: int):
    with db.session_scope() as s:
        p: Optional[db.Project] = db.Project.get(s, id)
        if p is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        return schema.Project.from_db(p)


@app.post(
    '/projectapi/project',
    description='Create project',
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            'model': schema.Project,
            'description': 'Successful response (created)',
        },
        status.HTTP_401_UNAUTHORIZED: {
            'description': 'Login failed (token is wrong)',
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'SkillTag not found.'
        }
    }
)
async def create_project(
    project: schema.ProjectCreate,
    token: Optional[str] = Cookie(None),
):
    # auth
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    username = user.auth(token)
    if username is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    # tag check
    if False in [user.tag_exist(t) for t in project.skilltags]:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            'SkillTag not found',
        )

    return project.create(username)


@app.patch(
    '/projectapi/project',
    description='Update project',
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            'model': schema.Project,
            'description': 'Successful response (updated)',
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'Resource not found.'
        },
        status.HTTP_401_UNAUTHORIZED: {
            'description': 'not logged in',
        },
    },
)
async def update_project(
    project_update: schema.ProjectUpdate,
    token: Optional[str] = Cookie(None),
):
    # Permission (admin only)
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    if (username := user.auth(token)) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    with db.session_scope() as s:
        p = db.Project.get(s, project_update.id)
        if p is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                'Project is not found (id is wrong)',
            )
        if username not in [au.username for au in p.admin_users]:
            raise HTTPException(status.HTTP_403_FORBIDDEN)

    # tag check
    if False in [user.tag_exist(t) for t in project_update.skilltags]:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            'SkillTag not found',
        )

    # Update
    result = project_update.update()
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    return result


@app.delete(
    '/projectapi/project/{id:int}',
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            'description': 'Successful response (deleted)',
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'Project not found',
        },
        status.HTTP_401_UNAUTHORIZED: {
            'description': 'login failed'
        },
        status.HTTP_403_FORBIDDEN: {
            'description': 'forbidden (admin only)'
        },
    },
)
async def delete_project(id: int, token: Optional[str] = Cookie(None)):
    with db.session_scope() as s:
        p = db.Project.get(s, id)
        if p is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        # permission
        if token is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)
        if (username := user.auth(token)) is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)

        if username not in [au.username for au in p.admin_users]:
            raise HTTPException(status.HTTP_403_FORBIDDEN)

        p.is_active = False
        s.commit()


# Like

@app.get(
    '/projectapi/project/{id:int}/like',
    description='Get users who likes project',
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            'model': schema.Likes,
            'description': 'Successful response (liked)',
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'Project not found',
        },
    },
)
def get_likes(id: int):
    with db.session_scope() as s:
        p = db.Project.get(s, id)
        if p is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        return schema.Likes.get_from_project(p)


@app.patch(
    '/projectapi/project/{id:int}/like',
    description='like to project',
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            'description': 'Successful response (liked)',
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            'description': 'Already liked',
        },
        status.HTTP_401_UNAUTHORIZED: {
            'description': 'Cookie token is required.',
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'Project not found.',
        },
    }
)
async def like(id: int, token: Optional[str] = Cookie(None)):
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    username: Optional[str] = user.auth(token)
    if username is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    with db.session_scope() as s:
        p = db.Project.get(s, id)
        if p is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        user_proj_likes = s.query(db.Like).filter(
            db.Like.username == username
        ).filter(
            db.Like.project_id == id
        )
        if user_proj_likes.count() > 0:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS)

        like = db.Like(username=username, project_id=p.id)
        s.add(like)
        s.commit()

        return


@app.delete(
    '/projectapi/project/{id:int}/like',
    description='unlike to project',
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            'description': 'Successful response (unliked)',
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            'description': 'Already unliked/not liked yet',
        },
        status.HTTP_401_UNAUTHORIZED: {
            'description': 'Cookie token is required.',
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'Project not found.',
        },
    }
)
def unlike(id: int, token: Optional[str] = Cookie(None)):
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    username: Optional[str] = user.auth(token)
    if username is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    with db.session_scope() as s:
        likes = s.query(db.Like).filter(
            db.Like.username == username
        ).filter(
            db.Like.project_id == id
        )

        if likes.count() < 1:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS)

        likes.delete()
        s.commit()

    return


# Member
@app.post(
    '/projectapi/project/{proj_id:int}/members/',
    description='Join user as member_type',
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            'model': List[str],
            'description': 'Successful response (list of username)'
        },
        status.HTTP_401_UNAUTHORIZED: {
            'description': 'not logged in',
        },
        status.HTTP_403_FORBIDDEN: {
            'description': 'permitted (only for admin user)',
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'Project/User not found',
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            'description': 'already joined',
        },
    },
)
async def join_member(
    proj_id: int, project_join: schema.ProjectJoin,
    token: Optional[str] = Cookie(None),
):
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    if (username := user.auth(token)) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

    if user.exist(project_join.username) is False:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            'User not found',
        )

    with db.session_scope() as s:
        if (p := db.Project.get(s, proj_id)) is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                'Project not found',
            )

        # permission (admin only)
        if username not in [au.username for au in p.admin_users]:
            raise HTTPException(status.HTTP_403_FORBIDDEN)

        # already joined?
        if project_join.type == schema.MemberType.MEMBER:
            if project_join.username in [x.username for x in p.members]:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS)
        if project_join.type == schema.MemberType.ANNOUNCE:
            if project_join.username in [x.username for x in p.announce_users]:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS)
        if project_join.type == schema.MemberType.ADMIN:
            if project_join.username in [x.username for x in p.admin_users]:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS)

        # join
        all_type = [
            schema.MemberType.MEMBER,
            schema.MemberType.ANNOUNCE,
            schema.MemberType.ADMIN
        ]
        if project_join.type in all_type:
            # member, announce, admin
            mem_list = [x.username for x in p.members]
            if project_join.username not in mem_list:
                pu = db.ProjectUser(
                    project_id=proj_id,
                    username=project_join.username
                )
                s.add(pu)
        if project_join.type in all_type[1:]:
            # announce, admin
            au_list = [x.username for x in p.announce_users]
            if project_join.username not in au_list:
                au = db.ProjectAnnounceUser(
                    project_id=proj_id,
                    username=project_join.username,
                )
                s.add(au)
        if project_join.type in all_type[2:]:
            # admin
            adu_list = [x.username for x in p.admin_users]
            if project_join.username not in adu_list:
                adu = db.ProjectAdminUser(
                    project_id=proj_id,
                    username=project_join.username,
                )
                s.add(adu)

        s.commit()


# Search
@app.get(
    '/projectapi/project/search',
    description='Search Project',
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            'model': schema.ProjectSearchResult,
            'description':
                'Successful Response (sorted by levenshtein distance)',
        },
    },
)
async def search_project(
    title: str,
    limit: int,
    offset: int,
):
    return schema.ProjectSearchResult.search(title, limit, offset)


# User
@app.get(
    '/projectapi/project/{username:str}',
    description='Projects in which the user joins',
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            'model': List[schema.Project],
            'description': 'Successful response',
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'User not found',
        },
    },
)
async def projects_of_user(username: str):
    with db.session_scope() as s:
        proj_list = s.query(db.ProjectUser).filter(
            db.ProjectUser.username == username
        )
        return [
            schema.Project.from_db(pu.project)
            for pu in proj_list
            if pu.project.is_active
        ]
