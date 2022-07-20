<template>
    <div>
        <v-progress-linear
            color="primary accent-4"
            indeterminate
            rounded
            height="4"
            :active="loading"
        ></v-progress-linear>
        <div>
            <div>
                <v-row>
                    <v-col>
                        <v-checkbox v-model="pitschionly" label="Pitschi'd projects only" @change="checkboxChanged"></v-checkbox>
                    </v-col>
                    <v-col cols="12" sm="6" md="3">
                        <v-text-field
                            v-model="filteredId"
                            append-icon="mdi-magnify"
                            label="Search By ID"
                            single-line
                            hide-details
                            @click:append="filterById"
                            :rules="numberRules"
                        ></v-text-field>
                    </v-col>
                </v-row>
            </div>
            <v-data-table
                :headers="projectsTableHeaders"
                :items="projects"
                item-key="id"
                class="elevation-1"
                multi-sort
                :items-per-page="10"
                :sort-by="['id']"
                :sort-desc="[false, true]"
                height="400px" width="100%"
            >
                <template #item.projectlink="{ item }">
                    <a :href="item.projectlink">
                    {{ item.id }}
                    </a>
                </template>

                <template #item.collectionlink="{ item }">
                    <a :href="item.collectionlink">
                    {{ item.collection }}
                    </a>
                </template>
            </v-data-table>
        </div>
        <br />
        <div align="center">
            <v-btn color="primary" @click="syncProjects">
                Manually sync projects with PPMS
            </v-btn>
        </div>
    </div>
</template>

<script>
    import Vue from 'vue'
    import ProjectAPI from "@/api/ProjectAPI"

    export default {
        name: 'Projects',

        data() {
            return {
                allprojects: [],
                projects: [],
                loading: false,
                pitschionly: true,
                filteredId: null,
                projectsTableHeaders: [
                    { text: 'Project Id', value: 'projectlink' },
                    { text: 'Core Id', value: 'coreid' },
                    { text: 'Collection', value: 'collectionlink' },
                    { text: 'Description', value: 'description' },
                ],
                numberRules: [
                    value => value && value >= 0 || 'Must be 0 or a positive number'
                ],
            }
        },
        methods: {
            async refresh(){
                Vue.$log.info("refresh ...")
                if (this.$keycloak.hasRealmRole("dashboard")){
                    this.loading = true
                    this.allprojects = await ProjectAPI.getProjects()
                    this.allprojects.forEach(aproj => {
                        // this is slow, move it to backend ? 
                        aproj.projectlink = '/project?id=' + aproj.id
                        if(aproj.collection){
                            aproj.collectionlink = '/collection?id=' + aproj.collection
                        }
                    });
                    if (this.pitschionly) {
                        let pitchiedOnlyProjects = []
                        this.allprojects.forEach(aproj => {
                            if(aproj.collection){
                                pitchiedOnlyProjects.push(aproj)    
                            }
                        });
                        this.projects = pitchiedOnlyProjects
                    } else {
                        this.projects = this.allprojects 
                    }
                    this.loading = false               
                }
                else {
                    Vue.$log.info("not has dashboard access ...")
                }
            },

            async checkboxChanged(){
                if (this.pitschionly) {
                    let pitchiedOnlyProjects = []
                    this.allprojects.forEach(aproj => {
                        if(aproj.collection)
                            pitchiedOnlyProjects.push(aproj)    
                    });
                    this.projects = pitchiedOnlyProjects
                } else {
                    this.projects = this.allprojects 
                }
            },

            async syncProjects(){
                console.log("Start manual sync")
                this.loading = true
                await ProjectAPI.manualSync()
                console.log("Finish manual sync")
                this.loading = false
            }, 

            async filterById(){
                this.projects = []
                if (this.filteredId){
                    this.allprojects.forEach(aproj => {
                    if(aproj.id === parseInt(this.filteredId))
                        this.projects = [aproj]
                    });
                }
            }
        },
        mounted: async function() {
            this.refresh()
        },

    }
</script>