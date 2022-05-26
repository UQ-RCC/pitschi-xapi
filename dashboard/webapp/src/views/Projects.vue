<template>
    <div>
        <v-progress-linear
            color="primary accent-4"
            indeterminate
            rounded
            height="4"
            :active="loading"
        ></v-progress-linear>

    </div>
</template>

<script>
    import Vue from 'vue'
    import ProjectAPI from "@/api/ProjectAPI"

    export default {
        name: 'Projects',

        data() {
            return {
                projects: [],
                refreshPending: false,
            }
        },
        methods: {
            async refresh(){
                Vue.$log.info("refresh ...")
                if (this.$keycloak.hasRealmRole("superadmin")){
                    this.refreshPending = true
                    this.projects = await ProjectAPI.getProjects()                
                }
                else {
                    Vue.$log.info("not superadmin ...")
                }
            },
        },
        mounted: async function() {
            this.refresh()
        },

    }
</script>