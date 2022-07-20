<template>
    <div>
        <v-progress-linear
            color="primary accent-4"
            indeterminate
            rounded
            height="4"
            :active="loading"
        ></v-progress-linear>
        <v-card v-if="project">
            <v-list-item two-line>
                <v-list-item-content>
                    <v-list-item-title>ID</v-list-item-title>
                    <v-list-item-subtitle>{{ project.id }}</v-list-item-subtitle>
                </v-list-item-content>
            </v-list-item>
            <v-list-item two-line>
                <v-list-item-content>
                    <v-list-item-title>Collection</v-list-item-title>
                    <v-list-item-subtitle><a :href="'/collection?id=' + project.collection"> {{ project.collection }} </a></v-list-item-subtitle>
                </v-list-item-content>
            </v-list-item>
            <v-list-item>
                <v-list-item-content>
                    <v-list-item-title>Users</v-list-item-title>
                    <v-list-item-subtitle>
                        <li v-for="item in project.userslist" :key=item>
                            <b>username</b>: {{ item.username }} <b>email</b>: {{ item.email}}  
                            <b>userid</b>: {{ item.userid }} <b>name</b>: {{item.name}}
                        </li>
                    </v-list-item-subtitle>
                </v-list-item-content>
            </v-list-item>
            <v-list-item two-line>
                <v-list-item-content>
                    <v-list-item-title>Description</v-list-item-title>
                    <v-list-item-subtitle>{{ project.description }}</v-list-item-subtitle>
                </v-list-item-content>
            </v-list-item>

        </v-card>
        <div v-else>
            There is no project with ID {{ projectid }}
        </div>
    </div>
</template>

<script>
    import ProjectAPI from "@/api/ProjectAPI"

    export default {
        name: 'Project',

        data() {
            return {
                loading: false,
                projectid: 0, 
                project: null
            }
        },
        methods: {
        },
        mounted: async function() {
            this.loading = true
            this.projectid = this.$route.query.id
            this.project = await ProjectAPI.getProject(this.projectid)
            this.loading = false

        },

    }
</script>